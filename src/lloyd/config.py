"""Configuration management for Lloyd."""

import os
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
