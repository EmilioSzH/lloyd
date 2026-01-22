"""Configuration management for Lloyd."""

import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# LLM Model Configuration
# Use Ollama with local models (no API key required)
DEFAULT_LLM = "ollama/qwen2.5:14b"


def get_llm() -> str:
    """Get the configured LLM model string for CrewAI.

    Returns:
        LLM model string (e.g., 'ollama/qwen2.5:14b').
    """
    return os.environ.get("LLOYD_LLM", DEFAULT_LLM)


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
