"""
Agent Skills loader — the MCP tools that give the agent progressive disclosure
over the skills bundled in this repo's top-level `skills/` directory.

A *tool* does an action; a *skill* is packaged know-how about when and how to use
tools. `list_skills` shows the catalog (name + description only); `load_skill`
returns one skill's full methodology, loaded on demand once the agent decides it
is relevant.
"""
import os
import glob

# tools/ is at <repo>/tools ; skills live at <repo>/skills
SKILLS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skills"
)


def _parse_skill(path):
    """Return (name, description, body) from a SKILL.md with YAML frontmatter."""
    text = open(path, "r", errors="replace").read()
    name = os.path.basename(os.path.dirname(path))
    description, body = "", text.strip()
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            frontmatter, body = parts[1], parts[2].strip()
            for line in frontmatter.splitlines():
                key, sep, val = line.partition(":")
                if not sep:
                    continue
                key, val = key.strip().lower(), val.strip()
                if key == "name" and val:
                    name = val
                elif key == "description":
                    description = val
    return name, description, body


def register(mcp):

    @mcp.tool()
    def list_skills():
        """List the agent skills available, each with its name and description only. Call this first when facing a task to discover which specialized methodologies you can load. A skill packages know-how about when and how to use tools; loading one gives you a proven workflow to follow."""
        print("\n[TOOL] list_skills\n")
        catalog = []
        for path in sorted(glob.glob(os.path.join(SKILLS_DIR, "*", "SKILL.md"))):
            try:
                name, description, _ = _parse_skill(path)
                catalog.append({"name": name, "description": description})
            except Exception as e:  # noqa: BLE001
                catalog.append({"name": os.path.basename(os.path.dirname(path)), "error": str(e)})
        return {"skills": catalog}

    @mcp.tool()
    def load_skill(name: str):
        """Load the full instructions for a named agent skill (a name from list_skills). Returns the skill's methodology; follow it step by step. Call this once you decide a skill is relevant to the current goal."""
        print(f"\n[TOOL] load_skill -> {name}\n")
        path = os.path.join(SKILLS_DIR, name, "SKILL.md")
        if not os.path.isfile(path):
            available = [
                os.path.basename(os.path.dirname(p))
                for p in glob.glob(os.path.join(SKILLS_DIR, "*", "SKILL.md"))
            ]
            return {"error": f"skill '{name}' not found", "available": available}
        skill_name, _, body = _parse_skill(path)
        return {"name": skill_name, "instructions": body}
