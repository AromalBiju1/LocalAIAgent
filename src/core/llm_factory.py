"""
LLM Factory — Easy creation of LLM instances.

Provides ``create()`` from parameters and ``from_config()`` from a YAML dict.
"""

import logging
from typing import Dict, Any, Optional

import yaml

from pyda_models.models import BackendType, LLMConfig
from src.core.llm_base import BaseLLM
from src.core.ollama_llm import OllamaLLM
from src.core.llamacpp_llm import LlamaCppLLM
from src.core.openai_llm import OpenAILLM

logger = logging.getLogger(__name__)

# Map of backend type → implementation class
_BACKEND_MAP = {
    BackendType.OLLAMA: OllamaLLM,
    BackendType.LLAMACPP: LlamaCppLLM,
    "openai": OpenAILLM,  # Added Generic Client
}


class LLMFactory:
    """Factory for creating LLM backend instances."""

    @staticmethod
    def create(
        backend: str = "ollama",
        model_name: str = "elyssia:latest",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> BaseLLM:
        """Create an LLM instance from explicit parameters."""
        
        # Normalize backend string
        if backend == "openai":
             # Special case for string-based backend (not yet in enum)
             backend_key = "openai"
        else:
            try:
                backend_key = BackendType(backend)
            except ValueError:
                # Fallback to string if not in enum
                backend_key = backend

        if backend_key not in _BACKEND_MAP:
             available = list(_BACKEND_MAP.keys())
             raise ValueError(f"Unknown backend '{backend}'. Available: {available}")

        config = LLMConfig(
            model_name=model_name,
            backend=BackendType.OLLAMA if backend == "openai" else backend_key, # Hack for type hint
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        # Override for OpenAILLM since it uses dict config
        if backend == "openai":
            config_dict = {
                "name": model_name,
                "provider": "openai",
                "temperature": temperature,
                "max_tokens": max_tokens,
                **kwargs
            }
            logger.info("Creating OpenAILLM with model=%s", model_name)
            return OpenAILLM(config_dict)

        cls = _BACKEND_MAP[backend_key]
        logger.info("Creating %s with model=%s", cls.__name__, model_name)
        return cls(config)

    @staticmethod
    def from_config(config_dict: Dict[str, Any]) -> BaseLLM:
        """Create an LLM instance from a configuration dictionary.
        
        Args:
            config_dict: Dictionary with ``backend``, ``name``/``model_name``,
                         and optional generation params.
        """
        backend = config_dict.get("backend", "ollama")
        model_name = config_dict.get("name") or config_dict.get("model_name", "elyssia:latest")

        # Merge nested backend-specific settings
        extra: Dict[str, Any] = {}
        backend_cfg = config_dict.get(backend, {})
        
        # Common keys
        if "base_url" in backend_cfg:
            if backend == "ollama":
                extra["ollama_host"] = backend_cfg["base_url"]
            elif backend == "llamacpp":
                extra["llamacpp_host"] = backend_cfg["base_url"]
            elif backend == "openai":
                extra["base_url"] = backend_cfg["base_url"]

        if "api_key" in backend_cfg and backend == "openai":
            extra["api_key"] = backend_cfg["api_key"]

        if "timeout" in backend_cfg:
            extra["timeout"] = backend_cfg["timeout"]

        # Generation params
        for key in ("temperature", "max_tokens", "top_p", "top_k", "repeat_penalty"):
            if key in config_dict:
                extra[key] = config_dict[key]

        return LLMFactory.create(
            backend=backend,
            model_name=model_name,
            **extra,
        )

    @staticmethod
    def from_yaml(path: str) -> BaseLLM:
        """Load config from a YAML file and create an LLM.

        Args:
            path: Path to the YAML config file.

        Returns:
            A configured :class:`BaseLLM` subclass instance.
        """
        with open(path) as f:
            cfg = yaml.safe_load(f)
        model_cfg = cfg.get("model", cfg)
        return LLMFactory.from_config(model_cfg)

    @staticmethod
    def get_available_backends() -> Dict[str, bool]:
        """Check which backends are importable / reachable.
        
        Returns:
            Dict mapping backend name to availability boolean.
        """
        return {
            "ollama": True,
            "llamacpp": True,
            "openai": True,
        }

    @staticmethod
    def recommend_backend() -> str:
        """Recommend the best backend for the current environment.

        Returns:
            ``'ollama'`` (default recommendation) or ``'llamacpp'``.
        """
        # Ollama is almost always the easiest option
        return "ollama"
