from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from brand_os.workflows.content_draft import build_content_draft
from director_os.workflows.weekly_update import build_weekly_update
from interview_os.workflows.interview_brief import build_interview_brief
from one_on_one_os.workflows.meeting_brief import build_meeting_brief
from packages.shared.schemas.brand_os import BrandContentDraftRequest, BrandContentDraftResponse
from packages.shared.schemas.director_os import WeeklyUpdateRequest, WeeklyUpdateResponse
from packages.shared.schemas.interview_os import InterviewBriefRequest, InterviewBriefResponse
from packages.shared.schemas.one_on_one_os import OneOnOneRequest, OneOnOneResponse


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

    @server.tool()
    def interview_os_brief(request: InterviewBriefRequest) -> InterviewBriefResponse:
        """Run the Interview OS brief workflow from an MCP client."""
        return build_interview_brief(request)

    @server.tool()
    def one_on_one_os_brief(request: OneOnOneRequest) -> OneOnOneResponse:
        """Run the One-on-One OS meeting brief workflow from an MCP client."""
        return build_meeting_brief(request)

    return server


def main() -> None:
    """Run the standalone MCP server over stdio for Claude Desktop or Claude Code."""
    create_server().run("stdio")


if __name__ == "__main__":
    main()
