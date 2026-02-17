"""
FastAPI Server — ElyssiaAgent backend.

Run with:
    uvicorn src.api.server:app --reload --port 8000
    # or
    python run.py --mode web
"""

import logging
import os
import sys
import yaml
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.core.llm_factory import LLMFactory
from src.tools.base import ToolRegistry
from src.plugins.plugin_loader import PluginLoader
from src.api.routes import router, init_globals

# ── Logging ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("elyssia.api")


# ── Lifespan ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("🚀 Starting ElyssiaAgent backend...")

    # Create data directories
    for d in ["data/conversations", "data/vectorstore", "data/documents"]:
        os.makedirs(d, exist_ok=True)

    # Load config
    config_path = os.environ.get(
        "ELYSSIA_CONFIG",
        os.path.join(os.path.dirname(__file__), "..", "..", "config", "config.yaml"),
    )
    config_path = os.path.abspath(config_path)

    if os.path.exists(config_path):
        llm = LLMFactory.from_yaml(config_path)
        logger.info("Loaded config from %s", config_path)
    else:
        llm = LLMFactory.create(backend="ollama", model_name="qwen3:4b")
        logger.info("Using default config (Ollama qwen3:4b)")

    # Init memory (Initialize BEFORE LLM so history works even if LLM is down)
    from src.memory.memory import ConversationMemory
    memory = ConversationMemory(db_path="data/conversations/memory.db", memory_window=10)
    logger.info("💾 Memory initialized (%d conversations)", memory.stats()["conversations"])

    # Init LLM session (with timeout to prevent hanging)
    import asyncio
    try:
        logger.info("Initializing LLM session...")
        await asyncio.wait_for(llm.ensure_session(), timeout=5.0)
    except asyncio.TimeoutError:
        logger.warning("⚠️  LLM initialization timed out (backend might be slow/down)")
    except Exception as e:
        logger.warning("⚠️  LLM initialization failed: %s", e)

    # Health check
    try:
        healthy = await llm.check_health()
        if healthy:
            logger.info("✅ LLM backend is healthy")
        else:
            logger.warning("⚠️  LLM backend health check failed")
    except Exception as e:
        logger.warning("⚠️  Could not reach LLM backend: %s", e)

    # Init RAG pipeline (with timeout)
    rag_pipeline = None
    try:
        from src.rag.pipeline import RAGPipeline
        logger.info("Initializing RAG pipeline...")
        
        # NOTE: If RAGPipeline does heavy model loading in __init__, it WILL block the loop.
        # Ideally it should be loaded in a thread or have an async .initialize() method.
        # We will attempt to run it in a thread to avoid blocking the loop if it's CPU bound/blocking IO.
        
        def _load_rag():
            return RAGPipeline(
                persist_dir="data/vectorstore",
                collection_name="documents",
            )
        
        rag_pipeline = await asyncio.to_thread(_load_rag)
        logger.info("📚 RAG pipeline ready (%d documents)", rag_pipeline.stats()["document_count"])
    except Exception as e:
        logger.warning("⚠️  RAG pipeline unavailable: %s", e)

    # ── Plugin-based tool loading ──
    plugin_loader = PluginLoader()
    registry = ToolRegistry()

    loaded = await plugin_loader.load_all()
    plugin_loader.register_into(registry)

    logger.info("🧩 Loaded %d plugins", loaded)

    # Inject dependencies into tools that need them
    from src.tools.rag_tool import set_rag_pipeline
    from src.tools.summarize import set_llm as set_summarize_llm
    if rag_pipeline:
        set_rag_pipeline(rag_pipeline)
    set_summarize_llm(llm)

    logger.info("🔧 Registered %d tools: %s", len(registry), [t.name for t in registry.list_tools()])

    # ── Channel manager ──
    from src.channels.channel_manager import ChannelManager
    channel_manager = ChannelManager(llm=llm, tool_registry=registry, memory=memory)

    # Load channel config
    if os.path.exists(config_path):
        with open(config_path) as f:
            full_config = yaml.safe_load(f) or {}
        channels_created = channel_manager.setup_from_config(full_config)
        if channels_created:
            started = await channel_manager.start_all()
            logger.info("📡 Started %d/%d channels", started, channels_created)
        else:
            logger.info("📡 No channels configured (add 'channels:' to config.yaml)")
    else:
        logger.info("📡 No channels configured")

    # Inject into routes
    init_globals(
        llm, registry,
        memory=memory,
        rag_pipeline=rag_pipeline,
        plugin_loader=plugin_loader,
        channel_manager=channel_manager,
    )

    logger.info("✅ ElyssiaAgent backend ready on http://0.0.0.0:8000")

    yield  # ── app runs here ──

    # Shutdown
    logger.info("Shutting down ElyssiaAgent backend...")
    await channel_manager.stop_all()
    await plugin_loader.unload_all()
    await llm.close()


# ── App ──────────────────────────────────────────────────

app = FastAPI(
    title="ElyssiaAgent",
    description="Local AI Agent with tool calling, streaming, and web UI",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow Next.js dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth router removed by user request
# app.include_router(auth_router)

# Mount API routes
app.include_router(router)


# Root
@app.get("/")
async def root():
    return {
        "name": "ElyssiaAgent",
        "version": "1.0.0",
        "docs": "/docs",
        "api": "/api/health",
    }
