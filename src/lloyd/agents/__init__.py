"""Agent definitions for AEGIS."""

from lloyd.agents.analyst import AnalystAgent
from lloyd.agents.architect import ArchitectAgent
from lloyd.agents.base import AgentConfig, BaseAgent
from lloyd.agents.coder import CoderAgent
from lloyd.agents.researcher import ResearcherAgent
from lloyd.agents.reviewer import ReviewerAgent
from lloyd.agents.tester import TesterAgent
from lloyd.agents.writer import WriterAgent

__all__ = [
    "AgentConfig",
    "BaseAgent",
    "AnalystAgent",
    "ArchitectAgent",
    "ResearcherAgent",
    "CoderAgent",
    "TesterAgent",
    "ReviewerAgent",
    "WriterAgent",
]
