"""Classify user intent to determine implementation approach."""

import re
from enum import Enum


class UserIntent(str, Enum):
    EXTENSION = "extension"  # New capability via plugin (safe, sandboxed)
    SELF_MOD = "self_mod"  # Change Lloyd itself (needs clone/test)
    NORMAL_TASK = "normal_task"  # Regular task, not about Lloyd


class IntentClassifier:
    """Automatically detect what the user wants to build."""

    # Signals that user wants to ADD a new integration/connection
    EXTENSION_PATTERNS = [
        r"connect\s+(my\s+)?(to\s+)?(\w+)",  # "connect my Notion", "connect to Spotify"
        r"integrate\s+(with\s+)?(\w+)",  # "integrate with Notion"
        r"sync\s+(with\s+|to\s+)?(\w+)",  # "sync with Notion", "sync to calendar"
        r"add\s+(\w+)\s+(integration|support|sync)",  # "add Notion integration"
        r"link\s+(my\s+)?(\w+)",  # "link my calendar"
        r"hook\s+(up\s+)?(to\s+)?(\w+)",  # "hook up to Slack"
        r"pull\s+(from|data\s+from)\s+(\w+)",  # "pull from Notion"
        r"push\s+(to)\s+(\w+)",  # "push to Google Drive"
    ]

    EXTENSION_KEYWORDS = [
        "api",
        "webhook",
        "oauth",
        "token",
        "integration",
        "sync",
        "connect",
        "external",
        "service",
        "third-party",
        "plugin",
    ]

    # Signals that user wants to CHANGE Lloyd itself
    SELF_MOD_PATTERNS = [
        r"(change|modify|update|fix|improve|optimize)\s+(lloyd|the\s+cli|the\s+gui|the\s+ui)",
        r"(lloyd|cli|gui|ui)\s+(should|needs\s+to|could)",
        r"make\s+(lloyd|the\s+cli|the\s+gui)\s+(\w+)",
        r"(add|change|update)\s+(a\s+)?(command|button|panel|tab|theme|color|style)",
        r"(lloyd'?s?)\s+(inbox|metrics|knowledge|brainstorm)",
        r"modify\s+your\s+(own|self)",  # "modify your own..."
        r"change\s+your\s+(own|self)",  # "change your own..."
        r"your\s+own\s+(code|flow|orchestrator|source)",  # "your own code/flow"
        r"(src/lloyd|lloyd/src|flow\.py|main\.py)",  # Direct file references
        r"(yourself|your\s+code|your\s+behavior)",  # Self-referential
    ]

    SELF_MOD_KEYWORDS = [
        "lloyd",
        "cli",
        "gui",
        "theme",
        "color",
        "style",
        "panel",
        "command",
        "button",
        "interface",
        "layout",
        "font",
        "dark mode",
        "inbox",
        "metrics",
        "dashboard",
        "yourself",
        "your own",
    ]

    # Known external services (strong extension signal)
    EXTERNAL_SERVICES = {
        "notion",
        "spotify",
        "slack",
        "discord",
        "calendar",
        "google",
        "dropbox",
        "github",
        "gitlab",
        "trello",
        "asana",
        "todoist",
        "obsidian",
        "roam",
        "evernote",
        "airtable",
        "zapier",
        "ifttt",
        "twitter",
        "x",
        "linkedin",
        "instagram",
        "youtube",
        "twitch",
        "openai",
        "anthropic",
        "replicate",
        "huggingface",
        "aws",
        "azure",
        "firebase",
        "supabase",
        "mongodb",
        "postgres",
        "redis",
        "elasticsearch",
    }

    def classify(self, idea: str) -> tuple[UserIntent, str, float]:
        """
        Classify user intent.

        Returns:
            (intent, reason, confidence)
        """
        idea_lower = idea.lower()

        # Check for external service mentions (strong extension signal)
        for service in self.EXTERNAL_SERVICES:
            if service in idea_lower:
                return (UserIntent.EXTENSION, f"Detected external service: {service}", 0.9)

        # Check extension patterns
        for pattern in self.EXTENSION_PATTERNS:
            if re.search(pattern, idea_lower):
                return (UserIntent.EXTENSION, f"Matches extension pattern: {pattern}", 0.85)

        # Check self-mod patterns
        for pattern in self.SELF_MOD_PATTERNS:
            if re.search(pattern, idea_lower):
                return (UserIntent.SELF_MOD, f"Matches self-mod pattern: {pattern}", 0.85)

        # Keyword scoring
        ext_score = sum(1 for k in self.EXTENSION_KEYWORDS if k in idea_lower)
        mod_score = sum(1 for k in self.SELF_MOD_KEYWORDS if k in idea_lower)

        if ext_score > mod_score and ext_score >= 2:
            return (UserIntent.EXTENSION, f"Extension keywords: {ext_score}", 0.7)

        if mod_score > ext_score and mod_score >= 2:
            return (UserIntent.SELF_MOD, f"Self-mod keywords: {mod_score}", 0.7)

        # Default to normal task
        return (UserIntent.NORMAL_TASK, "No Lloyd-related signals", 0.8)

    def get_implementation_plan(self, intent: UserIntent, idea: str) -> dict:
        """Get the implementation approach for an intent."""
        if intent == UserIntent.EXTENSION:
            # Extract service name if possible
            service = self._extract_service(idea)
            return {
                "approach": "extension",
                "description": f"Build a sandboxed extension{f' for {service}' if service else ''}",
                "steps": [
                    "Create extension scaffold",
                    "Implement tool methods",
                    "Configure API keys if needed",
                    "Test in isolation",
                    "Enable for use",
                ],
                "safe": True,
                "needs_gpu": False,
                "can_break_lloyd": False,
            }

        elif intent == UserIntent.SELF_MOD:
            return {
                "approach": "self_modification",
                "description": "Modify Lloyd's code in an isolated clone",
                "steps": [
                    "Create safety snapshot",
                    "Create isolated clone",
                    "Make changes",
                    "Run tests (no GPU needed for most)",
                    "Preview changes",
                    "Approve or reject",
                ],
                "safe": True,  # Because we use clones
                "needs_gpu": "depends on changes",
                "can_break_lloyd": False,  # Clone protects us
            }

        else:
            return {
                "approach": "normal_task",
                "description": "Execute as regular Lloyd task",
                "steps": ["Process through normal flow"],
                "safe": True,
                "needs_gpu": True,
                "can_break_lloyd": False,
            }

    def _extract_service(self, idea: str) -> str | None:
        """Try to extract the service name from the idea."""
        idea_lower = idea.lower()
        for service in self.EXTERNAL_SERVICES:
            if service in idea_lower:
                return service.title()
        return None
