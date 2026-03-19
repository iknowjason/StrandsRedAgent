import re
import subprocess
from tools.tool_check import check_binary


def _is_dns_domain(value: str) -> bool:
    if not isinstance(value, str):
        return False
    domain = value.strip().lower().rstrip(".")
    if len(domain) < 3 or len(domain) > 253:
        return False
    pattern = re.compile(
        r"^(?=.{1,253}$)(?!-)(?:[a-z0-9-]{1,63}\.)+[a-z]{2,63}$",
        re.IGNORECASE,
    )
    return bool(pattern.match(domain))


def register(mcp):

    if not check_binary("subfinder"):
        return

    @mcp.tool()
    def subfinder(domain: str):
        """Passive subdomain discovery using subfinder. Only runs for valid DNS domains."""

        target = (domain or "").strip().lower().rstrip(".")

        if not _is_dns_domain(target):
            print(f"\n[TOOL] subfinder skipped -> invalid domain: {domain}\n")
            return {
                "status": "skipped",
                "reason": "Input is not a valid DNS domain (example: tesla.com).",
                "input": domain,
            }

        print(f"\n[TOOL] subfinder -> {target}\n")

        try:
            result = subprocess.run(
                ["subfinder", "-d", target],
                capture_output=True,
                text=True,
                timeout=45,
            )

            output_lines = [
                line.strip() for line in result.stdout.splitlines() if line.strip()
            ]
            return {
                "status": "ok" if result.returncode == 0 else "error",
                "domain": target,
                "subdomains": output_lines[:200],
                "count": len(output_lines),
                "stderr": result.stderr[:1200],
            }
        except Exception as exc:
            return {"status": "error", "domain": target, "error": str(exc)}
