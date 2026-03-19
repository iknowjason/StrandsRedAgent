import requests
import os
from tools.tool_check import check_env


def register(mcp):

    if not check_env("SERPER_API_KEY"):
        return

    @mcp.tool()
    def linkedin_recon(company: str):
        """Discover LinkedIn profiles for a target company using Serper API."""

        api_key = os.getenv("SERPER_API_KEY")

        print(f"\n[TOOL] linkedin_recon -> {company}\n")

        query = f"site:linkedin.com/in {company}"
        url = "https://google.serper.dev/search"

        r = requests.post(url, headers={"X-API-KEY": api_key}, json={"q": query})
        return r.json()
