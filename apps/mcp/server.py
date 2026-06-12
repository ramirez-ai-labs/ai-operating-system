from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from brand_os.workflows.content_draft import build_content_draft
from director_os.workflows.weekly_update import build_weekly_update
from packages.shared.schemas.brand_os import BrandContentDraftRequest, BrandContentDraftResponse
from packages.shared.schemas.director_os import WeeklyUpdateRequest, WeeklyUpdateResponse


def create_server() -> FastMCP:
    """Create the standalone MCP server exposing AI-OS workflows as tools."""
    server = FastMCP("ai-operating-system")

    @server.tool()
    def director_os_weekly_update(request: WeeklyUpdateRequest) -> WeeklyUpdateResponse:
        """Run the Director OS weekly update workflow from an MCP client."""
        return build_weekly_update(request)

    @server.tool()
    def brand_os_content_draft(request: BrandContentDraftRequest) -> BrandContentDraftResponse:
        """Run the Brand OS content-draft workflow from an MCP client."""
        return build_content_draft(request)

    return server


def main() -> None:
    """Run the standalone MCP server over stdio for Claude Desktop or Claude Code."""
    create_server().run("stdio")


if __name__ == "__main__":
    main()
