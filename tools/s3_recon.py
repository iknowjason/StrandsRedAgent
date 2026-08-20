"""
s3_recon — discover and loot a publicly exposed S3 bucket for a domain.

Anonymous / unauthenticated: uses `aws ... --no-sign-request`, so it only reads
what the bucket already serves to the public. Read-only. The `awscli` binary is
present in the MCP server image.

Loot is downloaded to a persistent directory (default: <repo>/loot/<domain>, or
$LOOT_DIR/<domain>) and a human-readable LOOT_REPORT.txt is written there listing
the local path of every file that was pulled down.
"""
import os
import subprocess
from datetime import datetime, timezone

# High-value key substrings, in triage priority order.
PRIORITY = (
    ".env", "config", "settings", "credential", ".pem", ".key",
    ".py", ".js", ".php", ".sql", ".db", ".sqlite", ".bak",
    "readme", "todo", "notes", ".json", ".yml", ".yaml", "docker-compose",
)

# Repo root is one level up from tools/. Loot lands here unless $LOOT_DIR overrides.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOOT_ROOT = os.environ.get("LOOT_DIR") or os.path.join(_REPO_ROOT, "loot")


def _aws(args, timeout=60):
    return subprocess.run(
        ["aws"] + args, capture_output=True, text=True, timeout=timeout
    )


def _human_size(raw):
    try:
        n = float(raw)
    except (TypeError, ValueError):
        return str(raw)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def _write_report(report_path, domain, bucket, listing, loot):
    """Write a readable, organized loot report to report_path."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    bar = "=" * 68
    rule = "-" * 68
    lines = [
        bar,
        " S3 LOOT REPORT",
        bar,
        f" Target domain    : {domain}",
        f" Listable bucket  : {bucket}",
        f" Generated (UTC)  : {now}",
        f" Loot directory   : {os.path.dirname(report_path)}",
        f" Objects in bucket: {len(listing)}",
        f" Files looted     : {len(loot)}",
        "",
        rule,
        " LOOTED FILES",
        rule,
    ]
    if not loot:
        lines.append("   (no high-value files were downloaded)")
    for i, item in enumerate(loot, 1):
        lines += [
            "",
            f" [{i}] {item['key']}",
            f"     size          : {_human_size(item['size'])}",
            f"     downloaded to : {item['download_path']}",
            "     preview       :",
        ]
        preview = (item.get("preview") or "").strip()
        if preview:
            for pl in preview.splitlines()[:12]:
                lines.append(f"       | {pl}")
            if len(preview.splitlines()) > 12:
                lines.append("       | ... (truncated — see file above for full contents)")
        else:
            lines.append("       | <empty or binary>")

    lines += ["", rule, f" ALL BUCKET OBJECTS ({len(listing)})", rule]
    for o in listing:
        lines.append(f"   {_human_size(o['size']):>9}  {o['key']}")
    lines.append("")

    with open(report_path, "w", errors="replace") as fh:
        fh.write("\n".join(lines))


def register(mcp):

    @mcp.tool()
    def s3_recon(domain: str, max_files: int = 15, max_bytes: int = 20000):
        """Discover and loot a publicly exposed S3 bucket for a domain. Lists the bucket anonymously (no credentials), downloads interesting files (.env, source code, database backups, READMEs) to a local loot directory, and writes a readable LOOT_REPORT.txt recording where each file was saved. Returns the loot contents and the report path so they can be triaged for leaked secrets and vulnerabilities. Read-only; use for authorized recon of a target hosted on Amazon S3."""
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
        size_by_key = {o["key"]: o["size"] for o in listing}
        loot_keys = [k for k in keys if any(p in k.lower() for p in PRIORITY)][:max_files]

        # 3. Download anonymously into a persistent per-domain loot directory,
        #    preserving the bucket's key structure so paths stay meaningful.
        loot_dir = os.path.join(LOOT_ROOT, domain)
        os.makedirs(loot_dir, exist_ok=True)

        loot = []
        for key in loot_keys:
            dest = os.path.join(loot_dir, key)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            dl = _aws(["s3", "cp", f"s3://{bucket}/{key}", dest, "--no-sign-request"])
            entry = {
                "key": key,
                "size": size_by_key.get(key, "?"),
                "download_path": dest,
            }
            if dl.returncode == 0 and os.path.isfile(dest):
                try:
                    entry["preview"] = open(dest, "r", errors="replace").read(max_bytes)
                except Exception as e:  # noqa: BLE001
                    entry["preview"] = f"<could not read: {e}>"
            else:
                entry["download_error"] = (dl.stderr or "download failed").strip()
            loot.append(entry)

        # 4. Write the readable loot report alongside the downloaded files.
        report_path = os.path.join(loot_dir, "LOOT_REPORT.txt")
        _write_report(report_path, domain, bucket, listing, loot)
        print(f"[TOOL] s3_recon wrote loot report -> {report_path}\n")

        return {
            "domain": domain,
            "listable_bucket": bucket,
            "object_count": len(listing),
            "objects": keys,
            "loot_dir": loot_dir,
            "report_path": report_path,
            "looted_files": {e["key"]: e.get("preview", "") for e in loot},
            "loot": [
                {k: v for k, v in e.items() if k != "preview"} for e in loot
            ],
        }
