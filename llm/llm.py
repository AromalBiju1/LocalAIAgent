""" LLM Interface  Abstraction layer for diff llm backends"""
import asyncio
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncIterator,Union
from dataclasses import dataclass
import json,logging,aiohttp

from pyda_models.models import MessageRole,BackendType,LLMConfig,LLMResponse,StreamChunk,ToolDefinition

@dataclass
class Message:
    """message structure for convo"""
    role:MessageRole
    content:str
    name:Optional[str]=None
    tool_calls:Optional[List[Dict[str, Any]]]=None
    tool_call_id : Optional[str] = None


# base llm interface


class BaseLLM(ABC):
    """abstract base class for llm backends"""

    def __inti__(self,config: LLMConfig):
        self.config = config
        self.session :Optional[aiohttp.ClientSession] = None


    async def __aenter__(self):
        """Async context manager entry """
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout)       
        ) 
    return self

    async def __aexit__(self,exc_type,exc_val,exc_tb):
     """async context manager exit"""
     if self.session:
        await self.session.close()




    @abstractmethod
    async def generate(
        self,messages:List[Message],
        tools:Optional[List[ToolDefinition]]=None,
        stream:bool = False
    )-> Union[LLMResponse,AsyncIterator[StreamChunk]]:
        """generate completion"""
        pass


    @abstractmethod
    async def count_tokens(self,text:str) -> int:
        """count tokens in text"""
        pass
 #ollama bacxend


class OllamaLLM(BaseLLM):
    def __init__(self,config: LLMConfig):
        super().__init__(config)
        self.base_url= config.ollama_host


    async def generate(
        self,messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        stream:bool = False  ) -> Union[LLMResponse, AsyncIterator[StreamChunk]]:
        """gen completion using ollama"""

        if stream:
            return self._stream_generate(messages,tools)  

        #non sreaming
        payload = self._build_payload(messages,tools,stream=False)   
        try:
            async with self.session.post(
                f"{self.base_url}/api/chat",
                json=payload) as response:

                response.raise_for_status()
                result = await response.json()

                return LLMResponse(
                    content=result.get("message",{}).get("content",""),
                    model=result.get("model",self.config.model_name),
                    tokens_used=result.get("eval_count"),
                    finish_reason=result.get("done_reason"),
                    tool_calls=results.get("message",{}).get("tool_calls")
                )
        except aiohttp.ClientError as e:
                    logger.error(f"Ollama API error :{e}")
                    raise RuntimeError(f"failed to generate completion: {e}")
        except Exception as e:
            logger.error(f"unexpected error : {e}")
            raise


    async def _stream_generate(self,messages: List[Message],
    tools:Optional[List[ToolDefinition]] = None)-> AsyncIterator[StreamChunk]:

        """stream completion from ollama"""

    payload = self._build_payload(message,tools,stream=True)
    try:
        async with self.session.post(
            f"{self.base_url}/api/chat",
            json=payload
        ) as response:
            response.raise_for_status()
            async for line in response.content:
                if line:
                    try:
                        chunk_data = json.load(line.decode('utf-8'))

                        yield StreamChunk(
                            content = chunk_data.get("message",{}.get("content","")),
                            done=chunk_data.get("done","False"),
                            tokens_used=chunk_data.get("eval_count")
                        )
                        if chunk_data.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue  

    except aiohttp.ClientError as e:
        logger.error(f"Ollama streaming error: {e}")
        raise RuntimeError(f"failed to stream completion:{e}")




def _build_payload(self, messages: List[Message], tools:Optional[List[ToolDefinition]],stream:bool)-> Dict[str,Any]:
    """ request payload building"""

    #convert to ollama format
    formatted_msg = []
    for msg in messages:
        message_dict = {
            "role": msg.role.value,
            "content": msg.content
        }
        if msg.tool_calls:
            message_dict["tool_calls"] = msg.tool_calls
        formatted_msg.append(message_dict)

    payload = {
        "model": self.config.model_name,
        "messages" : formatted_msg,
        "stream" : stream,
        "options": {
            "temperature" : self.config.temperature,
            "num_predict" : self.config.max_tokens,
            "top_p" : self.config.top_p,
            "top_k": self.config.top_k,
            "repeat_penalty" : self.config.repeat_penalty
        }
    }

    if self.config.stop_sequences:
        payload["options"]["stop"] = self.config.stop_sequences

    #tools
    if tools:
        payload["tools"]= [tool.model_dump() for tool in tools]  
    return payload

    async def  count_tokens(self,text:str)-> int:
        """approx token count for ollama
        note: ollama doesn't provide exact tokenisation , this is estimate"""
        #rough approx : ~4 chars per token

        return len(text)//4
    async def check_health(self)-> bool:
        """ check if ollama is running"""
        try:
            async with self.session.get(f"{self.base_url}/api/tags") as response:
                return response.status == 200
        except:
            logger.error(f"Health check failed:{e}")  
            return False




            # llama.cpp  backend

class LlamaCppLLM(BaseLLM):
    def __init__(self,config: LLMConfig):
        super().__init__(config)
        self.base_url= config.llamacpp_host


    async def generate(
        self,messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        stream:bool = False  ) -> Union[LLMResponse, AsyncIterator[StreamChunk]]:
        """gen completion using llama.cpp"""

        if stream:
            return self._stream_generate(messages,tools)  

        #non sreaming
        payload = self._build_payload(messages,tools,stream=False)   
        try:
            async with self.session.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload) as response:

                response.raise_for_status()
                result = await response.json()
                choice = result.get("choices", [{}])[0]
                message = choice.get("message", {})

                return LLMResponse(
                    content=message.get("content",""),
                    model=result.get("model",self.config.model_name),
                    tokens_used=result.get("usage",{}).get("total_tokens"),
                    finish_reason=choice.get("finish_reason"),
                    tool_calls=message.get("tool_calls")
                )
        except aiohttp.ClientError as e:
                    logger.error(f"llama.cpp API error :{e}")
                    raise RuntimeError(f"failed to generate completion: {e}")
        except Exception as e:
            logger.error(f"unexpected error : {e}")
            raise


    async def _stream_generate(self,messages: List[Message],
    tools:Optional[List[ToolDefinition]] = None)-> AsyncIterator[StreamChunk]:

        """stream completion from llamacpp"""

    payload = self._build_payload(message,tools,stream=True)
    try:
        async with self.session.post(
            f"{self.base_url}/v1/chat/completions",
            json=payload
        ) as response:
            response.raise_for_status()
            async for line in response.content:
                if line:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith("data: "):
                            data_str = line_str[6:]
                            if data_str == "[DONE]":break
                            try:
                                chunk_data = json.loads(data_str)
                                choice = chunk_data.get("choices",[{}])[0]
                                delta = choice.get("delta",{})

                                yield StreamChunk(
                                    content = delta.get("content",""),
                                    done=choice.get("finish_reason") is not None,
                                    tokens_used=chunk_data.get("usage",{}).get("total_tokens")
                                )
                                if chunk_data.get("done"):
                                    break
                            except json.JSONDecodeError:
                                continue  

    except aiohttp.ClientError as e:
        logger.error(f"llamacpp streaming error: {e}")
        raise RuntimeError(f"failed to stream completion:{e}")




def _build_payload(self, messages: List[Message], tools:Optional[List[ToolDefinition]],stream:bool)-> Dict[str,Any]:
    """ request payload building"""

    #convert to ollama format
    formatted_msg = []
    for msg in messages:
        message_dict = {
            "role": msg.role.value,
            "content": msg.content
        }
        if msg.tool_calls:
            message_dict["tool_calls"] = msg.tool_calls
        formatted_msg.append(message_dict)

    payload = {
        "model": self.config.model_name,
        "messages" : formatted_msg,
        "stream" : stream,
        "options": {
            "temperature" : self.config.temperature,
            "num_predict" : self.config.max_tokens,
            "top_p" : self.config.top_p,
            "top_k": self.config.top_k,
            "repeat_penalty" : self.config.repeat_penalty
        }
    }

    if self.config.stop_sequences:
        payload["options"]["stop"] = self.config.stop_sequences

    #tools
    if tools:
        payload["tools"]= [tool.model_dump() for tool in tools]  
    return payload

    async def  count_tokens(self,text:str)-> int:
        """approx token count for ollama
        note: ollama doesn't provide exact tokenisation , this is estimate"""
        #rough approx : ~4 chars per token

        return len(text)//4
    async def check_health(self)-> bool:
        """ check if ollama is running"""
        try:
            async with self.session.get(f"{self.base_url}/api/tags") as response:
                return response.status == 200
        except:
            logger.error(f"Health check failed:{e}")  
            return False








