"""Web search tools for AEGIS agents."""

from typing import Any

from crewai.tools import tool


@tool("Web Search")
def web_search(query: str, max_results: int = 5) -> str:
    """Search the web for information.

    Uses DuckDuckGo as a free search provider.

    Args:
        query: Search query string.
        max_results: Maximum number of results to return.

    Returns:
        Search results as formatted text or error message.
    """
    try:
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

        if not results:
            return f"No results found for: {query}"

        formatted_results = []
        for i, result in enumerate(results, 1):
            formatted_results.append(
                f"{i}. {result.get('title', 'No title')}\n"
                f"   URL: {result.get('href', 'No URL')}\n"
                f"   {result.get('body', 'No description')}\n"
            )

        return "\n".join(formatted_results)

    except ImportError:
        return (
            "Error: duckduckgo-search package not installed. "
            "Install with: pip install duckduckgo-search"
        )
    except Exception as e:
        return f"Error performing web search: {e}"


@tool("Fetch Web Page")
def fetch_web_page(url: str) -> str:
    """Fetch and extract text content from a web page.

    Args:
        url: URL of the page to fetch.

    Returns:
        Extracted text content or error message.
    """
    try:
        import httpx
        from bs4 import BeautifulSoup

        response = httpx.get(url, timeout=30, follow_redirects=True)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()

        # Get text content
        text = soup.get_text(separator="\n", strip=True)

        # Limit output length
        max_chars = 10000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[Content truncated...]"

        return text

    except ImportError:
        return (
            "Error: Required packages not installed. "
            "Install with: pip install httpx beautifulsoup4"
        )
    except Exception as e:
        return f"Error fetching web page: {e}"


# Type alias for better readability
ToolFunc = Any

# Export web search tools
WEB_SEARCH_TOOLS: list[ToolFunc] = [web_search, fetch_web_page]
