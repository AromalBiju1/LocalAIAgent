"""
FastAPI Routes — Chat, streaming, models, tools, health endpoints.
"""

import json
import re
import time
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import StreamingResponse

from pyda_models.models import LLMConfig, MessageRole
from src.core.llm_base import Message
from src.core.llm_factory import LLMFactory
from src.core.ollama_llm import OllamaLLM
from src.tools.base import BaseTool, ToolRegistry
from src.tools.prompt_tools import inject_tool_prompt, parse_tool_calls
from src.api.schemas import (
    ChatRequest,
    ChatResponse,
    StreamEvent,
    ToolInfo,
    HealthResponse,
    ModelInfo,
    ChatMessage,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# ── Global state (set during server lifespan) ────────────
_llm = None
_tool_registry: Optional[ToolRegistry] = None
_memory = None
_rag_pipeline = None
_plugin_loader = None
_channel_manager = None
_start_time = time.time()


def init_globals(llm, registry: ToolRegistry, memory=None, rag_pipeline=None, plugin_loader=None, channel_manager=None):
    """Called by server lifespan to inject dependencies."""
    global _llm, _tool_registry, _memory, _rag_pipeline, _plugin_loader, _channel_manager
    _llm = llm
    _tool_registry = registry
    _memory = memory
    _rag_pipeline = rag_pipeline
    _plugin_loader = plugin_loader
    _channel_manager = channel_manager


def _to_messages(chat_msgs: list[ChatMessage]) -> list[Message]:
    """Convert API ChatMessages to internal Message objects."""
    return [
        Message(
            role=MessageRole(m.role),
            content=m.content,
            name=m.name,
            tool_calls=m.tool_calls,
            tool_call_id=m.tool_call_id,
        )
        for m in chat_msgs
    ]


# ── Health ────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
async def health():
    """Server health check."""
    healthy = False
    if _llm:
        try:
            healthy = await _llm.check_health()
        except Exception:
            pass

    return HealthResponse(
        status="ok" if healthy else "degraded",
        backend=_llm.config.backend.value if _llm else "none",
        model=_llm.config.model_name if _llm else "none",
        tools_count=len(_tool_registry) if _tool_registry else 0,
        uptime_seconds=round(time.time() - _start_time, 1),
    )


# ── Models ────────────────────────────────────────────────

@router.get("/models", response_model=list[ModelInfo])
async def list_models():
    """List available models."""
    if not _llm:
        raise HTTPException(503, "LLM not initialized")

    if isinstance(_llm, OllamaLLM):
        names = await _llm.list_models()
        return [ModelInfo(name=n) for n in names]

    return [ModelInfo(name=_llm.config.model_name)]


# ── Tools ─────────────────────────────────────────────────

@router.get("/tools", response_model=list[ToolInfo])
async def list_tools():
    """List registered tools."""
    if not _tool_registry:
        return []
    return [
        ToolInfo(name=t.name, description=t.description, parameters=t.parameters)
        for t in _tool_registry.list_tools()
    ]


# ── Chat (non-streaming) ─────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Generate a chat completion."""
    if not _llm:
        raise HTTPException(503, "LLM not initialized")

    messages = _to_messages(req.messages)

    # Build generation kwargs
    tools = _tool_registry.get_definitions() if (req.tools_enabled and _tool_registry) else None

    response = await _llm.generate(messages, tools=tools, stream=False)

    # If tool calls, execute them and get final response
    if response.tool_calls and _tool_registry:
        response = await _run_tool_loop(messages, response, max_iterations=5)

    return ChatResponse(
        content=response.content,
        model=response.model,
        tokens_used=response.tokens_used,
        finish_reason=response.finish_reason,
        tool_calls=response.tool_calls,
    )


# ── Chat (SSE streaming) ─────────────────────────────────

@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """Stream a chat completion via Server-Sent Events, with tool calling support."""
    if not _llm:
        raise HTTPException(503, "LLM not initialized")

    messages = _to_messages(req.messages)
    use_tools = req.tools_enabled and _tool_registry and len(_tool_registry) > 0

    # ── Save User Message to Memory ──
    if _memory and req.conversation_id:
        # We assume the last message is the new user input
        last_msg = messages[-1] if messages else None
        if last_msg and last_msg.role == MessageRole.USER:
            try:
                msg_id = _memory.add_message("user", last_msg.content, conversation_id=req.conversation_id)
                logger.info(f"📝 Saved USER message {msg_id} to conversation {req.conversation_id}")
            except Exception as e:
                logger.error(f"❌ Failed to save user message: {e}")
    else:
        logger.warning(f"⚠️ Memory not initialized or no conversation_id ({req.conversation_id})")

    async def event_generator():
        try:
            final_messages = list(messages)

            # ── Prompt-based tool calling ──
            if use_tools:
                # Inject tool descriptions into system prompt
                from datetime import datetime
                base_system = (
                    f"You are a helpful AI assistant. "
                    f"Today's date is {datetime.now().strftime('%B %d, %Y')}. "
                    f"Current time: {datetime.now().strftime('%I:%M %p')}."
                )
                tool_system = inject_tool_prompt(
                    base_system,
                    _tool_registry,
                )

                # Prepend or replace system message
                has_system = any(m.role == MessageRole.SYSTEM for m in final_messages)
                if has_system:
                    final_messages = [
                        Message(
                            role=m.role,
                            content=inject_tool_prompt(m.content, _tool_registry),
                            name=m.name,
                            tool_calls=m.tool_calls,
                            tool_call_id=m.tool_call_id,
                        ) if m.role == MessageRole.SYSTEM else m
                        for m in final_messages
                    ]
                else:
                    final_messages.insert(0, Message(
                        role=MessageRole.SYSTEM,
                        content=tool_system,
                    ))

                # Probe (non-streaming) to check if model wants to call a tool
                for iteration in range(5):
                    probe = await _llm.generate(final_messages, stream=False)
                    probe_text = probe.content or ""

                    # Strip Qwen3 <think> tags before parsing for tool calls
                    probe_text = re.sub(r"<think>[\s\S]*?</think>", "", probe_text).strip()

                    # Parse response for tool call blocks
                    tool_calls, clean_text = parse_tool_calls(probe_text)

                    if not tool_calls:
                        # No tool calls found — stream this response directly
                        # Send the probe content as a single token event
                        if clean_text:
                            yield f"data: {StreamEvent(event='token', content=clean_text, done=True, tokens_used=probe.tokens_used).model_dump_json()}\n\n"
                            yield "data: [DONE]\n\n"
                            return
                        break

                    # Execute each tool call
                    final_messages.append(Message(
                        role=MessageRole.ASSISTANT,
                        content=probe_text,
                    ))

                    for tc in tool_calls:
                        func = tc.get("function", tc)
                        tool_name = func.get("name", "")
                        tool_args_raw = func.get("arguments", "{}")

                        if isinstance(tool_args_raw, str):
                            try:
                                tool_args = json.loads(tool_args_raw)
                            except json.JSONDecodeError:
                                tool_args = {}
                        else:
                            tool_args = tool_args_raw

                        # Emit tool call event to frontend
                        yield f"data: {StreamEvent(event='tool_call', tool_name=tool_name, content=json.dumps(tool_args)).model_dump_json()}\n\n"

                        tool = _tool_registry.get(tool_name)
                        if tool:
                            result = await tool.execute(**tool_args)
                        else:
                            result = f"Tool '{tool_name}' not found."

                        # Emit tool result event
                        yield f"data: {StreamEvent(event='tool_result', tool_name=tool_name, tool_result=result).model_dump_json()}\n\n"

                        # Add tool result to conversation
                        final_messages.append(Message(
                            role=MessageRole.USER,
                            content=f"Tool '{tool_name}' returned:\n{result}\n\nPlease use this information to answer the original question.",
                        ))

            # Ensure date awareness even without tools
            if not use_tools:
                from datetime import datetime
                date_system = (
                    f"You are a helpful AI assistant. "
                    f"Today's date is {datetime.now().strftime('%B %d, %Y')}. "
                    f"Current time: {datetime.now().strftime('%I:%M %p')}."
                )
                has_system = any(m.role == MessageRole.SYSTEM for m in final_messages)
                if not has_system:
                    final_messages.insert(0, Message(role=MessageRole.SYSTEM, content=date_system))

            # ── Stream the final response ──
            gen = await _llm.generate(final_messages, stream=True)

            # Qwen3 CoT: track <think> tag state
            in_think = False
            think_buffer = ""
            token_buffer = ""
            full_response_text = ""  # Accumulate for memory

            async for chunk in gen:
                text = chunk.content or ""
                token_buffer += text
                full_response_text += text

                # Process buffer for think tags
                while token_buffer:
                    if in_think:
                        # Inside <think> — look for closing tag
                        close_idx = token_buffer.find("</think>")
                        if close_idx != -1:
                            # Capture remaining thinking text
                            think_buffer += token_buffer[:close_idx]
                            # Emit the complete thinking as a single event
                            if think_buffer.strip():
                                yield f"data: {StreamEvent(event='thinking', content=think_buffer.strip()).model_dump_json()}\n\n"
                            think_buffer = ""
                            in_think = False
                            token_buffer = token_buffer[close_idx + len("</think>"):]
                            # Skip leading newlines after </think>
                            token_buffer = token_buffer.lstrip("\n")
                        else:
                            # Still inside think — accumulate and wait
                            think_buffer += token_buffer
                            token_buffer = ""
                    else:
                        # Outside <think> — look for opening tag
                        open_idx = token_buffer.find("<think>")
                        if open_idx != -1:
                            # Emit any text before the tag
                            before = token_buffer[:open_idx]
                            if before:
                                yield f"data: {StreamEvent(event='token', content=before).model_dump_json()}\n\n"
                            in_think = True
                            token_buffer = token_buffer[open_idx + len("<think>"):]
                        elif "<think" in token_buffer and not token_buffer.endswith(">"):
                            # Partial tag — wait for more tokens
                            break
                        else:
                            # Normal text — emit it
                            yield f"data: {StreamEvent(event='token', content=token_buffer).model_dump_json()}\n\n"
                            token_buffer = ""

                if chunk.done:
                    # Flush any remaining buffers
                    if think_buffer.strip():
                        yield f"data: {StreamEvent(event='thinking', content=think_buffer.strip()).model_dump_json()}\n\n"
                    if token_buffer:
                        yield f"data: {StreamEvent(event='token', content=token_buffer).model_dump_json()}\n\n"
                    
                    # ── Save Assistant Response to Memory ──
                    if _memory and req.conversation_id:
                        clean_content = re.sub(r"<think>[\s\S]*?</think>", "", full_response_text).strip()
                        if clean_content:
                             try:
                                 msg_id = _memory.add_message("assistant", clean_content, conversation_id=req.conversation_id)
                                 logger.info(f"📝 Saved ASSISTANT message {msg_id} to conversation {req.conversation_id}")
                                 
                                 # Trigger auto-summarization in background
                                 if hasattr(_memory, 'auto_summarize'):
                                     import asyncio
                                     asyncio.create_task(_memory.auto_summarize(req.conversation_id, _llm))
                             except Exception as e:
                                 logger.error(f"❌ Failed to save assistant message: {e}")
                    
                    yield f"data: {StreamEvent(event='token', content='', done=True, tokens_used=chunk.tokens_used).model_dump_json()}\n\n"
                    break

        except Exception as e:
            logger.error("Stream error: %s", e)
            error_event = StreamEvent(event="error", content=str(e), done=True)
            yield f"data: {error_event.model_dump_json()}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── WebSocket streaming ──────────────────────────────────

@router.websocket("/ws/chat")
async def websocket_chat(ws: WebSocket):
    """WebSocket endpoint for real-time bidirectional chat."""
    await ws.accept()
    logger.info("WebSocket client connected")

    try:
        while True:
            data = await ws.receive_json()
            messages_data = data.get("messages", [])
            stream = data.get("stream", True)

            messages = [
                Message(
                    role=MessageRole(m["role"]),
                    content=m["content"],
                )
                for m in messages_data
            ]

            if not _llm:
                await ws.send_json({"event": "error", "content": "LLM not initialized"})
                continue

            if stream:
                gen = await _llm.generate(messages, stream=True)
                async for chunk in gen:
                    await ws.send_json({
                        "event": "token",
                        "content": chunk.content,
                        "done": chunk.done,
                    })
                    if chunk.done:
                        break
            else:
                response = await _llm.generate(messages)
                await ws.send_json({
                    "event": "message",
                    "content": response.content,
                    "tokens_used": response.tokens_used,
                    "done": True,
                })

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error("WebSocket error: %s", e)
        try:
            await ws.send_json({"event": "error", "content": str(e)})
        except Exception:
            pass


# ── Tool loop ─────────────────────────────────────────────

async def _run_tool_loop(messages, response, max_iterations=5):
    """Execute tools and feed results back to the LLM."""
    for _ in range(max_iterations):
        if not response.tool_calls:
            return response

        # Add assistant message with tool calls
        messages.append(Message(
            role=MessageRole.ASSISTANT,
            content=response.content or "",
            tool_calls=response.tool_calls,
        ))

        # Execute each tool call
        for tc in response.tool_calls:
            func = tc.get("function", tc)
            tool_name = func.get("name", "")
            tool_args_raw = func.get("arguments", "{}")

            if isinstance(tool_args_raw, str):
                try:
                    tool_args = json.loads(tool_args_raw)
                except json.JSONDecodeError:
                    tool_args = {}
            else:
                tool_args = tool_args_raw

            tool = _tool_registry.get(tool_name) if _tool_registry else None
            if tool:
                result = await tool.execute(**tool_args)
            else:
                result = f"Tool '{tool_name}' not found."

            messages.append(Message(
                role=MessageRole.TOOL,
                content=result,
                tool_call_id=tc.get("id", ""),
                name=tool_name,
            ))

        # Generate again with tool results
        tools = _tool_registry.get_definitions() if _tool_registry else None
        response = await _llm.generate(messages, tools=tools, stream=False)

    return response


# ── Memory endpoints ─────────────────────────────────────

@router.get("/memory/conversations")
async def list_conversations(limit: int = 20):
    """List recent conversations."""
    if not _memory:
        return []
    return _memory.list_conversations(limit=limit)


@router.get("/memory/conversations/{conv_id}")
async def get_conversation(conv_id: str):
    """Get conversation details and messages (smart context)."""
    if not _memory:
        raise HTTPException(503, "Memory not initialized")
    conv = _memory.get_conversation(conv_id)
    if not conv:
        raise HTTPException(404, "Conversation not found")
    
    # Use smart context window (summary + recent messages)
    try:
        messages = await _memory.get_context_window(conv_id, limit=20)
    except AttributeError:
         # Fallback if method missing
        messages = _memory.get_messages(conv_id)
        
    return {"conversation": conv, "messages": messages}


@router.get("/memory/search")
async def search_memory(q: str, limit: int = 10):
    """Search across all conversations."""
    if not _memory:
        return []
    return _memory.search(q, limit=limit)


@router.get("/memory/stats")
async def memory_stats():
    """Get memory statistics."""
    if not _memory:
        return {"conversations": 0, "messages": 0}
    return _memory.stats()


@router.delete("/memory/conversations/{conv_id}")
async def delete_conversation(conv_id: str):
    """Delete a conversation."""
    if not _memory:
        raise HTTPException(503, "Memory not initialized")
    _memory.delete_conversation(conv_id)
    return {"status": "deleted", "id": conv_id}


@router.post("/memory/conversations")
async def new_conversation(title: Optional[str] = None):
    """Start a new conversation."""
    if not _memory:
        raise HTTPException(503, "Memory not initialized")
    conv_id = _memory.new_conversation(title=title)
    return {"id": conv_id, "title": title}


# ── RAG endpoints ────────────────────────────────────────

@router.post("/rag/ingest")
async def rag_ingest(file_path: Optional[str] = None, text: Optional[str] = None, source: Optional[str] = None):
    """Ingest a file or text into the knowledge base."""
    if not _rag_pipeline:
        raise HTTPException(503, "RAG pipeline not initialized")

    if file_path:
        try:
            count = _rag_pipeline.ingest_file(file_path)
            return {"status": "ok", "chunks": count, "source": file_path}
        except FileNotFoundError:
            raise HTTPException(404, f"File not found: {file_path}")
    elif text:
        count = _rag_pipeline.ingest_text(text, source=source or "api_input")
        return {"status": "ok", "chunks": count, "source": source}
    else:
        raise HTTPException(400, "Provide file_path or text")


@router.get("/rag/search")
async def rag_search(q: str, top_k: int = 5):
    """Search the knowledge base."""
    if not _rag_pipeline:
        return {"results": [], "query": q}
    results = _rag_pipeline.search_raw(q, top_k=top_k)
    return {"results": results, "query": q}


@router.get("/rag/stats")
async def rag_stats():
    """Get RAG pipeline statistics."""
    if not _rag_pipeline:
        return {"document_count": 0, "status": "unavailable"}
    return _rag_pipeline.stats()


# ── Plugin Management ────────────────────────────────────

@router.get("/plugins")
async def list_plugins():
    """List all loaded plugins."""
    if not _plugin_loader:
        return {"plugins": [], "total": 0}
    return {
        "plugins": _plugin_loader.list_plugins(),
        "total": len(_plugin_loader.plugins),
    }


@router.get("/plugins/{name}")
async def get_plugin(name: str):
    """Get details about a specific plugin."""
    if not _plugin_loader:
        raise HTTPException(503, "Plugin system not initialized")
    plugin = _plugin_loader.get_plugin(name)
    if not plugin:
        raise HTTPException(404, f"Plugin not found: {name}")
    return plugin.to_dict()


@router.post("/plugins/{name}/reload")
async def reload_plugin(name: str):
    """Unload and reload a specific plugin."""
    if not _plugin_loader:
        raise HTTPException(503, "Plugin system not initialized")

    # Unload
    was_loaded = await _plugin_loader.unload_plugin(name)

    # Re-discover and load
    for meta in _plugin_loader.discover():
        if meta.name == name:
            result = await _plugin_loader.load_plugin(meta)
            if result and _tool_registry:
                for tool in result.get_tools():
                    _tool_registry.register(tool)
                return {"status": "reloaded", "plugin": result.to_dict()}

    if was_loaded:
        return {"status": "unloaded", "message": f"Plugin '{name}' unloaded but not found on re-discover"}
    raise HTTPException(404, f"Plugin not found: {name}")


@router.get("/plugins/stats/overview")
async def plugin_stats():
    """Get plugin system statistics."""
    if not _plugin_loader:
        return {"total_plugins": 0, "total_tools": 0}
    return _plugin_loader.stats()


# ── Channel Management ───────────────────────────────────

@router.get("/channels")
async def list_channels():
    """List all configured channels."""
    if not _channel_manager:
        return {"channels": [], "total": 0}
    return {
        "channels": _channel_manager.list_channels(),
        "total": len(_channel_manager._channels),
    }


@router.post("/channels/{channel_type}/start")
async def start_channel(channel_type: str):
    """Start a specific channel (e.g. telegram)."""
    if not _channel_manager:
        raise HTTPException(503, "Channel manager not initialized")
    
    success = await _channel_manager.start_channel(channel_type)
    if success:
        return {"status": "started", "channel": channel_type}
    raise HTTPException(500, f"Failed to start channel: {channel_type}")


@router.post("/channels/{channel_type}/stop")
async def stop_channel(channel_type: str):
    """Stop a specific channel."""
    if not _channel_manager:
        raise HTTPException(503, "Channel manager not initialized")
    
    success = await _channel_manager.stop_channel(channel_type)
    if success:
        return {"status": "stopped", "channel": channel_type}
    raise HTTPException(500, f"Failed to stop channel: {channel_type}")
