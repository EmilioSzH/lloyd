"""Base classes for Lloyd extensions."""

import functools
from collections.abc import Callable
from typing import Any


def tool_method(func: Callable) -> Callable:
    """Decorator to mark a method as a tool method.

    Tool methods are exposed to the LLM and can be called during execution.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)

    wrapper._is_tool_method = True  # type: ignore
    return wrapper


class ExtensionTool:
    """Base class for extension tools.

    Extensions should inherit from this class and implement tool methods
    decorated with @tool_method.
    """

    name: str = "unnamed"
    description: str = ""

    def __init__(self, config: dict | None = None):
        """Initialize the extension tool.

        Args:
            config: Configuration dictionary for the extension
        """
        self.config = config or {}

    def get_tool_methods(self) -> list[dict[str, Any]]:
        """Get all tool methods defined on this extension.

        Returns:
            List of tool method descriptors
        """
        methods = []
        for name in dir(self):
            attr = getattr(self, name)
            if callable(attr) and getattr(attr, "_is_tool_method", False):
                methods.append({"name": name, "description": attr.__doc__ or "", "method": attr})
        return methods
