"""Configuration management for Lloyd."""

import logging
import os
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Configure logger
logger = logging.getLogger(__name__)

# Suppress litellm verbose logging (especially the apscheduler warnings)
logging.getLogger("LiteLLM").setLevel(logging.WARNING)
logging.getLogger("litellm").setLevel(logging.WARNING)
logging.getLogger("litellm.litellm_core_utils").setLevel(logging.ERROR)

# Also suppress httpx/httpcore noise
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# LLM Model Configuration
# Use Ollama with qwen2.5:32b on remote RunPod (RTX 5090 GPU)
DEFAULT_LLM = "ollama/qwen2.5:32b"
DEFAULT_OLLAMA_HOST = "http://localhost:11434"  # Use SSH tunnel to RunPod


def get_ollama_host() -> str:
    """Get the Ollama server host URL.

    Returns:
        Ollama host URL (e.g., 'http://localhost:11434').
    """
    return os.environ.get("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)


def get_llm() -> str:
    """Get the configured LLM model string for CrewAI.

    Returns:
        LLM model string (e.g., 'ollama/qwen2.5:32b').
    """
    return os.environ.get("LLOYD_LLM", DEFAULT_LLM)


def get_llm_client() -> Any:
    """Get a LangChain-compatible LLM client for direct invocation.

    This returns an object with an .invoke() method for direct LLM calls
    outside of CrewAI.

    Returns:
        LangChain-compatible LLM client.
    """
    llm_string = get_llm()
    ollama_host = get_ollama_host()

    # Parse the model string (format: provider/model)
    if "/" in llm_string:
        provider, model = llm_string.split("/", 1)
    else:
        provider = "ollama"
        model = llm_string

    if provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
            return ChatOllama(model=model, base_url=ollama_host)
        except ImportError:
            # Fallback to langchain_community
            from langchain_community.chat_models import ChatOllama
            return ChatOllama(model=model, base_url=ollama_host)

    elif provider in ("openai", "gpt"):
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model)

    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model)

    else:
        # Default to Ollama
        try:
            from langchain_ollama import ChatOllama
            return ChatOllama(model=llm_string, base_url=ollama_host)
        except ImportError:
            from langchain_community.chat_models import ChatOllama
            return ChatOllama(model=llm_string, base_url=ollama_host)


class LloydSettings(BaseSettings):
    """Lloyd configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="LLOYD_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM Configuration (optional - Ollama doesn't require API keys)
    # anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    # openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")

    # Tool Integrations
    composio_api_key: str | None = Field(default=None, alias="COMPOSIO_API_KEY")
    e2b_api_key: str | None = Field(default=None, alias="E2B_API_KEY")
    github_token: str | None = Field(default=None, alias="GITHUB_TOKEN")

    # Execution Limits
    max_iterations: int = Field(default=50)
    timeout_minutes: int = Field(default=60)
    rate_limit_per_hour: int = Field(default=100)

    # Paths
    lloyd_dir: Path = Field(default=Path(".lloyd"))
    prd_path: Path = Field(default=Path(".lloyd/prd.json"))
    progress_path: Path = Field(default=Path(".lloyd/progress.txt"))


# Keep old name for backwards compatibility
AEGISSettings = LloydSettings


def get_settings() -> LloydSettings:
    """Get Lloyd settings instance."""
    return LloydSettings()


class LLMHealthChecker:
    """Check LLM service health and availability."""

    def __init__(self, base_url: str | None = None, timeout: float = 5.0):
        """Initialize the health checker.

        Args:
            base_url: Ollama server URL. Defaults to configured host.
            timeout: Request timeout in seconds.
        """
        self.base_url = base_url or get_ollama_host()
        self.timeout = timeout

    def check_ollama_sync(self) -> tuple[bool, str]:
        """Check if Ollama is responding (synchronous).

        Returns:
            Tuple of (available, details).
        """
        import httpx

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = data.get("models", [])
                    model_names = [m.get("name", "unknown") for m in models]
                    return True, f"{len(models)} models: {', '.join(model_names[:3])}"
                return False, f"HTTP {response.status_code}"
        except httpx.ConnectError:
            return False, f"Connection refused at {self.base_url}"
        except httpx.TimeoutException:
            return False, f"Timeout after {self.timeout}s"
        except Exception as e:
            return False, str(e)

    async def check_ollama_async(self) -> tuple[bool, str]:
        """Check if Ollama is responding (asynchronous).

        Returns:
            Tuple of (available, details).
        """
        import httpx

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = data.get("models", [])
                    model_names = [m.get("name", "unknown") for m in models]
                    return True, f"{len(models)} models: {', '.join(model_names[:3])}"
                return False, f"HTTP {response.status_code}"
        except Exception as e:
            return False, str(e)

    def check_model_available(self, model_name: str) -> tuple[bool, str]:
        """Check if a specific model is loaded.

        Args:
            model_name: Name of the model to check.

        Returns:
            Tuple of (available, details).
        """
        import httpx

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    for m in models:
                        if m.get("name") == model_name:
                            size = m.get("size", 0) / (1024 ** 3)  # Convert to GB
                            return True, f"Model loaded ({size:.1f}GB)"
                    return False, f"Model '{model_name}' not found"
                return False, f"HTTP {response.status_code}"
        except Exception as e:
            return False, str(e)

    def quick_check(self) -> bool:
        """Quick health check - just returns True/False.

        Returns:
            True if Ollama is available, False otherwise.
        """
        available, _ = self.check_ollama_sync()
        return available
