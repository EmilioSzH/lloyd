"""Extension manager for Lloyd."""

import importlib.util
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Extension:
    """Represents a loaded extension."""

    name: str
    display_name: str
    version: str
    description: str
    path: Path
    manifest: dict
    tool_instance: Any | None = None
    enabled: bool = True
    error: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "version": self.version,
            "description": self.description,
            "path": str(self.path),
            "enabled": self.enabled,
            "error": self.error,
            "has_tool": self.tool_instance is not None,
        }


class ExtensionManager:
    """Manages Lloyd extensions."""

    def __init__(self, lloyd_dir: Path | None = None):
        """Initialize the extension manager.

        Args:
            lloyd_dir: Lloyd data directory. Defaults to .lloyd
        """
        self.lloyd_dir = lloyd_dir or Path(".lloyd")
        self.extensions_dir = self.lloyd_dir / "extensions"
        self.extensions: dict[str, Extension] = {}

    def discover(self) -> list[Extension]:
        """Discover all available extensions.

        Returns:
            List of discovered extensions
        """
        self.extensions_dir.mkdir(parents=True, exist_ok=True)
        extensions = []

        for dir_path in self.extensions_dir.iterdir():
            if dir_path.is_dir() and not dir_path.name.startswith("."):
                manifest_path = dir_path / "manifest.yaml"
                if manifest_path.exists():
                    try:
                        ext = self._load_extension(dir_path)
                        extensions.append(ext)
                        self.extensions[ext.name] = ext
                    except Exception as err:
                        # Create error extension entry
                        ext = Extension(
                            name=dir_path.name,
                            display_name=dir_path.name,
                            version="?",
                            description="Error loading extension",
                            path=dir_path,
                            manifest={},
                            tool_instance=None,
                            enabled=False,
                            error=str(err),
                        )
                        extensions.append(ext)

        return extensions

    def _load_extension(self, dir_path: Path) -> Extension:
        """Load an extension from a directory.

        Args:
            dir_path: Path to extension directory

        Returns:
            Loaded extension
        """
        # Load manifest
        manifest_path = dir_path / "manifest.yaml"
        with open(manifest_path, encoding="utf-8") as f:
            manifest = yaml.safe_load(f)

        ext = Extension(
            name=manifest.get("name", dir_path.name),
            display_name=manifest.get("display_name", dir_path.name),
            version=manifest.get("version", "0.0.0"),
            description=manifest.get("description", ""),
            path=dir_path,
            manifest=manifest,
        )

        # Load config if exists
        config_path = dir_path / "config.yaml"
        config = {}
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}

        # Load tool class
        entry_point = manifest.get("entry_point", "tool.py")
        tool_path = dir_path / entry_point

        if tool_path.exists():
            spec = importlib.util.spec_from_file_location(f"ext_{ext.name}", tool_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Find ExtensionTool subclass
                from .base import ExtensionTool

                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, ExtensionTool)
                        and attr is not ExtensionTool
                    ):
                        ext.tool_instance = attr(config)
                        break

        return ext

    def get_extension(self, name: str) -> Extension | None:
        """Get an extension by name.

        Args:
            name: Extension name

        Returns:
            Extension if found
        """
        return self.extensions.get(name)

    def get_enabled_tools(self) -> list[Any]:
        """Get all enabled extension tools.

        Returns:
            List of tool instances
        """
        return [
            ext.tool_instance
            for ext in self.extensions.values()
            if ext.enabled and ext.tool_instance
        ]

    def enable_extension(self, name: str) -> bool:
        """Enable an extension.

        Args:
            name: Extension name

        Returns:
            True if enabled successfully
        """
        ext = self.extensions.get(name)
        if ext:
            ext.enabled = True
            return True
        return False

    def disable_extension(self, name: str) -> bool:
        """Disable an extension.

        Args:
            name: Extension name

        Returns:
            True if disabled successfully
        """
        ext = self.extensions.get(name)
        if ext:
            ext.enabled = False
            return True
        return False

    def list_all(self) -> list[Extension]:
        """List all extensions.

        Returns:
            List of all extensions
        """
        return list(self.extensions.values())
