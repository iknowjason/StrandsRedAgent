import subprocess
import requests
import os
from memory.campaign_memory import update


def register(mcp):

    @mcp.tool()
    def osint_pipeline(domain: str):
        """Full OSINT pipeline: WHOIS, crt.sh subdomain enumeration, HTTP headers, and Brave Search."""

        print(f"\n[TOOL] osint_pipeline -> {domain}\n")

        results = {}
        whois_data = ""
        subdomains = []
        headers_data = {}

        # WHOIS
        try:
            whois = subprocess.run(
                ["whois", domain], capture_output=True, text=True
            )
            whois_data = whois.stdout[:1500]
            results["whois"] = whois_data
        except Exception as e:
            results["whois"] = f"whois failed: {e}"

        # Subdomains via crt.sh
        try:
            r = requests.get(
                f"https://crt.sh/?q={domain}&output=json", timeout=10
            )
            results["crtsh"] = r.text[:1500]
            try:
                records = r.json()
                discovered = set()
                for rec in records:
                    value = rec.get("name_value", "")
                    for entry in value.splitlines():
                        entry = entry.strip().lower()
                        if entry and "*" not in entry:
                            discovered.add(entry)
                subdomains = sorted(discovered)[:200]
            except Exception:
                subdomains = []
        except Exception as e:
            results["crtsh"] = f"crt.sh lookup failed: {e}"

        # HTTP Headers
        try:
            r = requests.get(f"https://{domain}", timeout=5)
            headers_data = dict(r.headers)
            results["headers"] = headers_data
        except Exception as e:
            results["headers"] = f"header probe failed: {e}"

        # Brave Search (degrades gracefully)
        try:
            api_key = os.getenv("BRAVE_API_KEY")
            if api_key:
                url = "https://api.search.brave.com/res/v1/web/search"
                headers = {"X-Subscription-Token": api_key}
                r = requests.get(url, headers=headers, params={"q": domain})
                results["brave_search"] = r.json()
            else:
                results["brave_search"] = "BRAVE_API_KEY not configured - skipped"
        except Exception as e:
            results["brave_search"] = str(e)

        update("osint", "whois", whois_data if whois_data else results.get("whois"))
        update("osint", "subdomains", subdomains)
        update("osint", "headers", headers_data if headers_data else results.get("headers"))
        update("osint", "crtsh_raw", results.get("crtsh"))
        update("osint", "brave_search", results.get("brave_search"))

        return results
