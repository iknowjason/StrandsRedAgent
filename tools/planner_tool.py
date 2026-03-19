def register(mcp):

    @mcp.tool()
    def red_team_planner(company: str):
        """Plan red team operations by coordinating OSINT intelligence for a target company."""

        print(f"\n[TOOL] red_team_planner -> {company}\n")

        return {
            "company": company,
            "description": "OSINT intelligence gathered",
        }
