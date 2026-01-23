"""Scaffold for creating new extensions."""

from pathlib import Path


def create_extension_scaffold(name: str, description: str | None = None) -> Path:
    """Create a new extension scaffold.

    Args:
        name: Extension name (will be directory name)
        description: Extension description

    Returns:
        Path to created extension directory
    """
    ext_dir = Path(".lloyd") / "extensions" / name
    ext_dir.mkdir(parents=True, exist_ok=True)

    # Generate display name and class name
    display_name = name.replace("-", " ").replace("_", " ").title()
    class_name = "".join(w.title() for w in name.replace("-", "_").split("_"))
    desc = description or f"{display_name} extension"

    # Create manifest.yaml
    manifest_content = f"""name: {name}
display_name: {display_name}
version: 0.1.0
description: {desc}
entry_point: tool.py
requires:
  config: []
"""
    (ext_dir / "manifest.yaml").write_text(manifest_content)

    # Create tool.py
    tool_content = f'''"""
{display_name} extension for Lloyd.
{desc}
"""

from lloyd.extensions import ExtensionTool, tool_method


class {class_name}Tool(ExtensionTool):
    """Tool for {display_name}."""

    name = "{name}"
    description = "{desc}"

    @tool_method
    def main_action(self, text: str) -> str:
        """Main action for this extension.

        Args:
            text: Input text to process

        Returns:
            Processed result
        """
        # TODO: Implement your logic here
        return f"Result: {{text}}"
'''
    (ext_dir / "tool.py").write_text(tool_content)

    # Create config.yaml
    (ext_dir / "config.yaml").write_text("# Extension configuration\n")

    # Create README.md
    readme_content = f"""# {display_name}

{desc}

## Usage

Edit `tool.py` to implement your extension logic.

## Configuration

Add configuration requirements to `manifest.yaml` and values to `config.yaml`.
"""
    (ext_dir / "README.md").write_text(readme_content)

    return ext_dir
