from mcp.server import FastMCP

from tools import osint
from tools import linkedin
from tools import subfinder
from tools import osint_pipeline
from tools import planner_tool
from tools import phishing_tool
from tools import campaign_state
from tools import ses_phishing

from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("RedTeam MCP Server", port=8001)

print("\n--- Red Team MCP Server (port 8001) ---")
print("Registering tools...\n")

modules = [
    ("osint (brave_search)", osint),
    ("linkedin", linkedin),
    ("subfinder", subfinder),
    ("osint_pipeline", osint_pipeline),
    ("planner_tool", planner_tool),
    ("phishing_tool", phishing_tool),
    ("campaign_state", campaign_state),
    ("ses_phishing", ses_phishing),
]

for name, mod in modules:
    print(f"  [{name}]")
    mod.register(mcp)

print("\nTool registration complete.\n")


def main():
    try:
        mcp.run(transport="streamable-http")
    except KeyboardInterrupt:
        print("\nShutting down Red Team MCP server (Ctrl-C).")


if __name__ == "__main__":
    main()
