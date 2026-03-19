from memory.campaign_memory import get_all


def register(mcp):

    @mcp.tool()
    def create_campaign(target: str):
        """Initialize a new campaign tracking state for the given target."""

        return {
            "target": target,
            "osint_complete": False,
            "campaign_ready": False,
        }

    @mcp.tool()
    def show_campaign_memory():
        """Display the current campaign memory state including all gathered intelligence."""

        return get_all()
