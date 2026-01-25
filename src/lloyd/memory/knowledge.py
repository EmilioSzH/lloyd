"""Knowledge Base with enhanced query and learning capabilities for Lloyd.

This module provides the KnowledgeBase class that wraps KnowledgeStore with
additional functionality for:
- Similarity-based queries using keyword matching
- Recording outcomes from story execution
- Formatting learnings for prompt injection
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from lloyd.knowledge.models import LearningEntry
from lloyd.knowledge.store import KnowledgeStore


# Category keywords for auto-extraction
CATEGORY_KEYWORDS = {
    "auth": ["auth", "login", "logout", "jwt", "token", "session", "password", "oauth", "permission"],
    "database": ["database", "db", "sql", "query", "migration", "model", "orm", "postgres", "mysql", "sqlite"],
    "api": ["api", "endpoint", "rest", "graphql", "request", "response", "http", "route", "controller"],
    "testing": ["test", "pytest", "unittest", "mock", "fixture", "assert", "coverage", "spec"],
    "config": ["config", "env", "environment", "settings", "dotenv", "yaml", "json", "toml"],
    "ui": ["ui", "frontend", "react", "vue", "component", "css", "html", "render", "display"],
}


class KnowledgeBase:
    """Enhanced knowledge base with query and learning capabilities."""

    def __init__(self, lloyd_dir: Path | None = None) -> None:
        """Initialize the knowledge base.

        Args:
            lloyd_dir: Lloyd data directory. Defaults to .lloyd
        """
        self.lloyd_dir = lloyd_dir or Path(".lloyd")
        self.store = KnowledgeStore(self.lloyd_dir)
        self.learnings_file = self.lloyd_dir / "knowledge" / "learnings.json"

    def _ensure_dir(self) -> None:
        """Ensure the knowledge directory exists."""
        self.learnings_file.parent.mkdir(parents=True, exist_ok=True)

    def _tokenize(self, text: str) -> set[str]:
        """Tokenize text into lowercase words for matching.

        Args:
            text: Text to tokenize.

        Returns:
            Set of lowercase word tokens.
        """
        # Remove punctuation and split on whitespace
        words = re.findall(r'\b\w+\b', text.lower())
        return set(words)

    def query_similar(self, description: str, top_k: int = 3) -> list[LearningEntry]:
        """Query for entries similar to the given description.

        Uses keyword matching on description and category fields,
        scoring entries by: overlap * confidence * (1 + frequency * 0.1)

        Args:
            description: Description to match against.
            top_k: Number of top results to return.

        Returns:
            List of top_k entries sorted by score descending.
        """
        entries = self.store.list_all()

        if not entries:
            return []

        description_tokens = self._tokenize(description)
        scored: list[tuple[float, LearningEntry]] = []

        for entry in entries:
            # Tokenize entry's description and category
            entry_tokens = self._tokenize(entry.description)
            entry_tokens.update(self._tokenize(entry.category))
            entry_tokens.update(self._tokenize(entry.title))

            # Add tags as tokens
            for tag in entry.tags:
                entry_tokens.update(self._tokenize(tag))

            # Calculate overlap
            overlap = len(description_tokens & entry_tokens)

            if overlap > 0:
                # Score: overlap * confidence * (1 + frequency * 0.1)
                score = overlap * entry.confidence * (1 + entry.frequency * 0.1)
                scored.append((score, entry))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        return [entry for _, entry in scored[:top_k]]

    def _extract_category(self, text: str) -> str:
        """Auto-extract category from text content.

        Args:
            text: Text to analyze for category keywords.

        Returns:
            Detected category or "general" if none found.
        """
        text_lower = text.lower()

        category_scores: dict[str, int] = {}
        for category, keywords in CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                category_scores[category] = score

        if category_scores:
            return max(category_scores, key=category_scores.get)
        return "general"

    def _find_duplicate_pattern(
        self, entries: list[dict[str, Any]], description: str, category: str
    ) -> dict[str, Any] | None:
        """Find existing entry with similar description and category.

        Args:
            entries: List of existing entries.
            description: Description to match.
            category: Category to match.

        Returns:
            Matching entry dict or None.
        """
        desc_tokens = self._tokenize(description)

        for entry in entries:
            if entry.get("category") != category:
                continue

            entry_tokens = self._tokenize(entry.get("description", ""))
            overlap = len(desc_tokens & entry_tokens)

            # Consider it a duplicate if >60% overlap
            if desc_tokens and overlap / len(desc_tokens) > 0.6:
                return entry

        return None

    def record_outcome(
        self, story: dict[str, Any], result: dict[str, Any], success: bool
    ) -> LearningEntry:
        """Record a learning from story execution outcome.

        Success creates "positive_pattern" entries.
        Failure creates "avoid_this" entries with error context.
        Duplicate patterns increment frequency instead of creating new entries.

        Args:
            story: The story dict that was executed.
            result: The result dict from execution.
            success: Whether execution was successful.

        Returns:
            The created or updated LearningEntry.
        """
        self._ensure_dir()

        # Load existing learnings
        learnings: list[dict[str, Any]] = []
        if self.learnings_file.exists():
            with open(self.learnings_file) as f:
                learnings = json.load(f)

        # Extract info from story
        story_title = story.get("title", "")
        story_desc = story.get("description", "")
        combined_text = f"{story_title} {story_desc}"

        # Auto-extract category
        category = self._extract_category(combined_text)

        # Build entry type and description
        if success:
            entry_type = "positive_pattern"
            description = f"Successfully completed: {story_title}"
            context = story_desc
        else:
            entry_type = "avoid_this"
            error_msg = result.get("error", result.get("message", "Unknown error"))
            description = f"Failed: {story_title} - {error_msg}"
            context = f"Story: {story_desc}\nError: {error_msg}"

        # Check for duplicate
        existing = self._find_duplicate_pattern(learnings, description, category)

        if existing:
            # Increment frequency
            existing["frequency"] = existing.get("frequency", 1) + 1
            existing["last_applied"] = datetime.now().isoformat()

            # Adjust confidence
            if success:
                existing["confidence"] = min(1.0, existing.get("confidence", 0.5) + 0.1)
            else:
                existing["confidence"] = max(0.0, existing.get("confidence", 0.5) - 0.05)

            # Save updated learnings
            with open(self.learnings_file, "w") as f:
                json.dump(learnings, f, indent=2)

            return LearningEntry.from_dict(existing)

        # Create new entry
        entry = LearningEntry(
            category=category,
            title=f"{entry_type}: {story_title}",
            description=description,
            context=context,
            confidence=0.5 if success else 0.3,
            frequency=1,
            tags=[entry_type, category] + story.get("tags", []),
        )

        # Add to learnings and also to main store
        learnings.append(entry.to_dict())
        with open(self.learnings_file, "w") as f:
            json.dump(learnings, f, indent=2)

        # Also add to main knowledge store
        self.store.add(entry)

        return entry

    def format_for_prompt(self, entries: list[LearningEntry]) -> str:
        """Format learning entries for prompt injection.

        Creates sections for "What worked well" and "What to avoid".

        Args:
            entries: List of learning entries to format.

        Returns:
            Formatted string for prompt injection.
        """
        if not entries:
            return ""

        positive_patterns: list[str] = []
        avoid_patterns: list[str] = []

        for entry in entries:
            # Determine if positive or negative based on tags/title
            is_positive = (
                "positive_pattern" in entry.tags
                or "positive" in entry.title.lower()
                or entry.confidence >= 0.7
            )

            formatted = f"- {entry.title}: {entry.description}"
            if entry.context:
                formatted += f"\n  Context: {entry.context[:200]}"

            if is_positive:
                positive_patterns.append(formatted)
            else:
                avoid_patterns.append(formatted)

        sections = []

        if positive_patterns:
            sections.append("## What worked well (apply these patterns):\n" + "\n".join(positive_patterns))

        if avoid_patterns:
            sections.append("## What to avoid (learn from past failures):\n" + "\n".join(avoid_patterns))

        return "\n\n".join(sections)

    def get_learnings_for_story(self, story: dict[str, Any]) -> str:
        """Get formatted learnings relevant to a story.

        Convenience method that queries and formats in one call.

        Args:
            story: The story dict to find relevant learnings for.

        Returns:
            Formatted string for prompt injection.
        """
        description = f"{story.get('title', '')} {story.get('description', '')}"
        relevant = self.query_similar(description, top_k=5)
        return self.format_for_prompt(relevant)
