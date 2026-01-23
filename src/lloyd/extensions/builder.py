"""Build extensions from natural language descriptions."""

import re
from pathlib import Path

import yaml

from .scaffold import create_extension_scaffold


def build_extension_from_idea(idea: str) -> dict:
    """Build an extension from a natural language description.

    Example: "Connect my Notion so I can sync brain dumps"
    -> Creates notion-sync extension with appropriate methods

    Args:
        idea: Natural language description of what the user wants

    Returns:
        Dictionary with extension details
    """
    # Extract service name and purpose
    service = extract_service_name(idea)
    purpose = extract_purpose(idea)

    ext_name = f"{service.lower()}-sync" if service else "custom-extension"

    print(f"\n  Building extension: {ext_name}")
    print(f"  Service: {service or 'custom'}")
    print(f"  Purpose: {purpose}")

    # Create scaffold
    ext_path = create_extension_scaffold(ext_name, purpose)
    print(f"  Created: {ext_path}")

    # Generate smart tool.py based on the idea
    generate_smart_tool(ext_path, service, purpose, idea)

    # Generate config requirements
    generate_config_requirements(ext_path, service)

    print(f"\n  Extension created: {ext_name}")
    print(f"  Next: lloyd ext configure {ext_name}")

    return {
        "status": "created",
        "extension": ext_name,
        "path": str(ext_path),
        "needs_config": bool(service),
        "service": service,
    }


def extract_service_name(idea: str) -> str | None:
    """Extract the external service name from the idea.

    Args:
        idea: The idea description

    Returns:
        Service name if found
    """
    services = [
        "notion",
        "spotify",
        "slack",
        "discord",
        "calendar",
        "google",
        "dropbox",
        "github",
        "trello",
        "asana",
        "todoist",
        "obsidian",
    ]
    idea_lower = idea.lower()
    for service in services:
        if service in idea_lower:
            return service.title()
    return None


def extract_purpose(idea: str) -> str:
    """Extract what the user wants to do.

    Args:
        idea: The idea description

    Returns:
        Extracted purpose
    """
    patterns = [
        r"(sync|push|pull|connect|integrate|link)\s+(.+)",
        r"so\s+(?:i\s+can|that\s+i\s+can)\s+(.+)",
        r"to\s+(.+?)(?:\.|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, idea.lower())
        if match:
            return match.group(1) if len(match.groups()) == 1 else match.group(2)
    return idea[:50]


def generate_smart_tool(ext_path: Path, service: str | None, purpose: str, idea: str) -> None:
    """Generate a smarter tool.py based on the service.

    Args:
        ext_path: Path to extension directory
        service: Service name (e.g., "Notion")
        purpose: Extracted purpose
        idea: Original idea
    """
    class_name = (service or "Custom").replace("-", "").replace("_", "").title()

    # Service-specific templates
    if service and service.lower() == "notion":
        tool_code = f'''"""
Notion integration for Lloyd.
Purpose: {purpose}
"""

from lloyd.extensions import ExtensionTool, tool_method


class {class_name}Tool(ExtensionTool):
    """Notion integration tool."""

    name = "notion"
    description = "Sync content with Notion"

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.api_key = self.config.get("NOTION_API_KEY")
        self.database_id = self.config.get("NOTION_DATABASE_ID")

    @tool_method
    def sync_to_notion(self, content: str, title: str = None) -> str:
        """Sync content to Notion.

        Args:
            content: Content to sync
            title: Page title (optional)

        Returns:
            URL of created page
        """
        if not self.api_key:
            return "Error: Configure NOTION_API_KEY first (lloyd ext configure notion-sync)"

        # TODO: Implement with notion-client
        # from notion_client import Client
        # client = Client(auth=self.api_key)
        # ...

        return f"Would sync to Notion: {{title or 'Untitled'}}"

    @tool_method
    def query_notion(self, query: str) -> list:
        """Search Notion for content.

        Args:
            query: Search query

        Returns:
            List of matching pages
        """
        if not self.api_key:
            return "Error: Configure NOTION_API_KEY first"

        # TODO: Implement search
        return f"Would search Notion for: {{query}}"
'''

    elif service and service.lower() == "spotify":
        tool_code = f'''"""
Spotify integration for Lloyd.
Purpose: {purpose}
"""

from lloyd.extensions import ExtensionTool, tool_method


class {class_name}Tool(ExtensionTool):
    """Spotify integration tool."""

    name = "spotify"
    description = "Control Spotify playback"

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.client_id = self.config.get("SPOTIFY_CLIENT_ID")
        self.client_secret = self.config.get("SPOTIFY_CLIENT_SECRET")

    @tool_method
    def play(self, query: str = None) -> str:
        """Play music or resume playback.

        Args:
            query: Optional search query

        Returns:
            Status message
        """
        return f"Would play: {{query or 'current track'}}"

    @tool_method
    def pause(self) -> str:
        """Pause playback.

        Returns:
            Status message
        """
        return "Would pause playback"

    @tool_method
    def search(self, query: str) -> str:
        """Search for tracks, albums, or artists.

        Args:
            query: Search query

        Returns:
            Search results
        """
        return f"Would search: {{query}}"
'''

    elif service and service.lower() == "slack":
        tool_code = f'''"""
Slack integration for Lloyd.
Purpose: {purpose}
"""

from lloyd.extensions import ExtensionTool, tool_method


class {class_name}Tool(ExtensionTool):
    """Slack integration tool."""

    name = "slack"
    description = "Send messages to Slack"

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.token = self.config.get("SLACK_TOKEN")

    @tool_method
    def send_message(self, channel: str, message: str) -> str:
        """Send a message to a Slack channel.

        Args:
            channel: Channel name or ID
            message: Message to send

        Returns:
            Status message
        """
        if not self.token:
            return "Error: Configure SLACK_TOKEN first"
        return f"Would send to #{{channel}}: {{message}}"
'''

    else:
        # Generic template
        tool_code = f'''"""
{service or "Custom"} extension for Lloyd.
Purpose: {purpose}
Original idea: {idea}
"""

from lloyd.extensions import ExtensionTool, tool_method


class {class_name}Tool(ExtensionTool):
    """{service or "Custom"} tool."""

    name = "{(service or "custom").lower()}"
    description = "{purpose}"

    def __init__(self, config: dict = None):
        super().__init__(config)

    @tool_method
    def main_action(self, input_text: str) -> str:
        """Main action for this extension.

        Args:
            input_text: Input to process

        Returns:
            Result
        """
        # TODO: Implement your logic here
        return f"Processed: {{input_text}}"
'''

    (ext_path / "tool.py").write_text(tool_code)


def generate_config_requirements(ext_path: Path, service: str | None) -> None:
    """Generate manifest with config requirements.

    Args:
        ext_path: Path to extension directory
        service: Service name
    """
    config_reqs = []

    if service:
        service_lower = service.lower()
        if service_lower == "notion":
            config_reqs = [
                {"key": "NOTION_API_KEY", "description": "Notion API token", "secret": True},
                {
                    "key": "NOTION_DATABASE_ID",
                    "description": "Default database ID",
                    "secret": False,
                },
            ]
        elif service_lower == "spotify":
            config_reqs = [
                {"key": "SPOTIFY_CLIENT_ID", "description": "Spotify Client ID", "secret": False},
                {
                    "key": "SPOTIFY_CLIENT_SECRET",
                    "description": "Spotify Client Secret",
                    "secret": True,
                },
            ]
        elif service_lower in ["slack", "discord"]:
            config_reqs = [
                {
                    "key": f"{service_lower.upper()}_TOKEN",
                    "description": f"{service} Bot Token",
                    "secret": True,
                }
            ]
        elif service_lower == "github":
            config_reqs = [
                {
                    "key": "GITHUB_TOKEN",
                    "description": "GitHub Personal Access Token",
                    "secret": True,
                }
            ]

    # Update manifest
    manifest_path = ext_path / "manifest.yaml"
    with open(manifest_path, encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    manifest["requires"] = {"config": config_reqs}

    with open(manifest_path, "w", encoding="utf-8") as f:
        yaml.dump(manifest, f, default_flow_style=False)
