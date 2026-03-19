import requests
import os
from tools.tool_check import check_env


def register(mcp):

    if not check_env("BRAVE_API_KEY"):
        return

    @mcp.tool()
    def brave_search(query: str):
        """Search the web using Brave Search API for OSINT intelligence gathering."""

        print(f"[TOOL EXECUTION] brave_search -> {query}")

        api_key = os.getenv("BRAVE_API_KEY")

        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {"X-Subscription-Token": api_key}

        r = requests.get(url, headers=headers, params={"q": query})
        return r.json()
