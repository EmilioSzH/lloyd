"""Tools for AEGIS agents."""

from typing import Any

from lloyd.tools.code_exec import CODE_EXEC_TOOLS, execute_python_sandbox, install_package_sandbox
from lloyd.tools.filesystem import (
    FILESYSTEM_TOOLS,
    create_directory,
    delete_file,
    list_directory,
    read_file,
    write_file,
)
from lloyd.tools.github import (
    GITHUB_TOOLS,
    create_github_issue,
    get_all_github_tools,
    list_github_issues,
    search_github_code,
    search_github_repos,
)
from lloyd.tools.shell import (
    SHELL_TOOLS,
    execute_shell,
    run_pytest,
    run_python_script,
    run_ruff,
)
from lloyd.tools.web_search import WEB_SEARCH_TOOLS, fetch_web_page, web_search

# Tool name to function mapping
TOOL_REGISTRY: dict[str, Any] = {
    # Filesystem tools
    "file_read": read_file,
    "file_write": write_file,
    "list_directory": list_directory,
    "create_directory": create_directory,
    "delete_file": delete_file,
    # Shell tools
    "shell": execute_shell,
    "run_python": run_python_script,
    "run_pytest": run_pytest,
    "run_ruff": run_ruff,
    # Code execution tools
    "code_exec": execute_python_sandbox,
    "install_package": install_package_sandbox,
    # GitHub tools
    "github": get_all_github_tools,  # Returns list of tools
    "github_search": search_github_repos,
    "github_search_code": search_github_code,
    "github_create_issue": create_github_issue,
    "github_list_issues": list_github_issues,
    # Web search tools
    "web_search": web_search,
    "fetch_web_page": fetch_web_page,
}


def get_tools_by_names(names: list[str]) -> list[Any]:
    """Get tool instances by their names.

    Args:
        names: List of tool names to retrieve.

    Returns:
        List of tool instances.
    """
    tools = []
    for name in names:
        if name in TOOL_REGISTRY:
            tool_or_getter = TOOL_REGISTRY[name]
            # Handle tool getters (like github which returns a list)
            if callable(tool_or_getter) and name == "github":
                tools.extend(tool_or_getter())
            else:
                tools.append(tool_or_getter)
    return tools


def get_all_tools() -> list[Any]:
    """Get all available tools.

    Returns:
        List of all tool instances.
    """
    all_tools = []
    all_tools.extend(FILESYSTEM_TOOLS)
    all_tools.extend(SHELL_TOOLS)
    all_tools.extend(CODE_EXEC_TOOLS)
    all_tools.extend(get_all_github_tools())
    all_tools.extend(WEB_SEARCH_TOOLS)
    return all_tools


__all__ = [
    # Registry and helpers
    "TOOL_REGISTRY",
    "get_tools_by_names",
    "get_all_tools",
    # Tool collections
    "FILESYSTEM_TOOLS",
    "SHELL_TOOLS",
    "CODE_EXEC_TOOLS",
    "GITHUB_TOOLS",
    "WEB_SEARCH_TOOLS",
    # Individual tools - Filesystem
    "read_file",
    "write_file",
    "list_directory",
    "create_directory",
    "delete_file",
    # Individual tools - Shell
    "execute_shell",
    "run_python_script",
    "run_pytest",
    "run_ruff",
    # Individual tools - Code execution
    "execute_python_sandbox",
    "install_package_sandbox",
    # Individual tools - GitHub
    "get_all_github_tools",
    "search_github_repos",
    "search_github_code",
    "create_github_issue",
    "list_github_issues",
    # Individual tools - Web search
    "web_search",
    "fetch_web_page",
]
