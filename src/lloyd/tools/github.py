"""GitHub operations via Composio integration."""

import os
from typing import Any

from crewai.tools import tool


def _get_composio_tools() -> list[Any]:
    """Get GitHub tools via Composio if available.

    Returns:
        List of Composio GitHub tools or empty list.
    """
    api_key = os.environ.get("COMPOSIO_API_KEY")
    if not api_key:
        return []

    try:
        from composio_crewai import Action, ComposioToolSet

        toolset = ComposioToolSet()

        tools = toolset.get_tools(
            actions=[
                Action.GITHUB_CREATE_AN_ISSUE,
                Action.GITHUB_CREATE_A_PULL_REQUEST,
                Action.GITHUB_LIST_REPOSITORY_ISSUES,
                Action.GITHUB_GET_A_REPOSITORY,
                Action.GITHUB_CREATE_OR_UPDATE_FILE_CONTENTS,
                Action.GITHUB_LIST_COMMITS,
                Action.GITHUB_SEARCH_CODE,
                Action.GITHUB_SEARCH_REPOSITORIES,
            ]
        )
        return tools
    except ImportError:
        return []
    except Exception:
        return []


@tool("Search GitHub Repositories")
def search_github_repos(query: str, max_results: int = 10) -> str:
    """Search for GitHub repositories.

    Args:
        query: Search query string.
        max_results: Maximum number of results to return.

    Returns:
        Search results as formatted text or error message.
    """
    # This is a fallback implementation using the GitHub API directly
    # Composio provides more comprehensive functionality when available
    import subprocess

    try:
        result = subprocess.run(
            ["gh", "search", "repos", query, "--limit", str(max_results)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return result.stdout or "No repositories found."
        return f"Error searching repos: {result.stderr}"
    except FileNotFoundError:
        return "Error: GitHub CLI (gh) not installed. Install it or configure COMPOSIO_API_KEY."
    except Exception as e:
        return f"Error: {e}"


@tool("Search GitHub Code")
def search_github_code(query: str, repo: str | None = None, max_results: int = 10) -> str:
    """Search for code in GitHub repositories.

    Args:
        query: Code search query.
        repo: Optional repository to search within (owner/repo format).
        max_results: Maximum number of results to return.

    Returns:
        Search results as formatted text or error message.
    """
    import subprocess

    try:
        cmd = ["gh", "search", "code", query, "--limit", str(max_results)]
        if repo:
            cmd.extend(["--repo", repo])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return result.stdout or "No code found."
        return f"Error searching code: {result.stderr}"
    except FileNotFoundError:
        return "Error: GitHub CLI (gh) not installed. Install it or configure COMPOSIO_API_KEY."
    except Exception as e:
        return f"Error: {e}"


@tool("Create GitHub Issue")
def create_github_issue(repo: str, title: str, body: str) -> str:
    """Create an issue in a GitHub repository.

    Args:
        repo: Repository in owner/repo format.
        title: Issue title.
        body: Issue body/description.

    Returns:
        Created issue URL or error message.
    """
    import subprocess

    try:
        result = subprocess.run(
            ["gh", "issue", "create", "--repo", repo, "--title", title, "--body", body],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return f"Issue created: {result.stdout.strip()}"
        return f"Error creating issue: {result.stderr}"
    except FileNotFoundError:
        return "Error: GitHub CLI (gh) not installed. Install it or configure COMPOSIO_API_KEY."
    except Exception as e:
        return f"Error: {e}"


@tool("List GitHub Issues")
def list_github_issues(repo: str, state: str = "open", max_results: int = 20) -> str:
    """List issues in a GitHub repository.

    Args:
        repo: Repository in owner/repo format.
        state: Issue state filter (open, closed, all).
        max_results: Maximum number of results.

    Returns:
        List of issues or error message.
    """
    import subprocess

    try:
        result = subprocess.run(
            ["gh", "issue", "list", "--repo", repo, "--state", state, "--limit", str(max_results)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return result.stdout or "No issues found."
        return f"Error listing issues: {result.stderr}"
    except FileNotFoundError:
        return "Error: GitHub CLI (gh) not installed. Install it or configure COMPOSIO_API_KEY."
    except Exception as e:
        return f"Error: {e}"


# Type alias for better readability
ToolFunc = Any

# Export GitHub tools (basic fallback + composio if available)
GITHUB_TOOLS: list[ToolFunc] = [
    search_github_repos,
    search_github_code,
    create_github_issue,
    list_github_issues,
]


def get_all_github_tools() -> list[Any]:
    """Get all GitHub tools including Composio tools if available.

    Returns:
        Combined list of GitHub tools.
    """
    composio_tools = _get_composio_tools()
    if composio_tools:
        return composio_tools
    return GITHUB_TOOLS
