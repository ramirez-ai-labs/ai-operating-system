from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from packages.shared.schemas.brand_os import BrandContentDraftRequest, BrandContentDraftResponse
from packages.shared.schemas.director_os import WeeklyUpdateRequest, WeeklyUpdateResponse
from packages.shared.schemas.interview_os import InterviewBriefRequest, InterviewBriefResponse
from packages.shared.schemas.one_on_one_os import OneOnOneRequest, OneOnOneResponse

# Workflow modules are imported inside each tool, not at module load. They pull
# in LangGraph, LangChain, LangSmith, and ChromaDB, which on a cold start can
# take longer than an MCP client's connect timeout (30s in Claude Code). The
# schemas above are plain Pydantic, so the server can answer `initialize` and
# `tools/list` immediately and defer the heavy imports to the first tool call.


def create_server() -> FastMCP:
    """Create the standalone MCP server exposing AI-OS workflows as tools."""
    server = FastMCP("ai-operating-system")

    @server.tool()
    def director_os_weekly_update(request: WeeklyUpdateRequest) -> WeeklyUpdateResponse:
        """Run the Director OS weekly update workflow from an MCP client."""
        from director_os.workflows.weekly_update import build_weekly_update

        return build_weekly_update(request)

    @server.tool()
    def brand_os_content_draft(request: BrandContentDraftRequest) -> BrandContentDraftResponse:
        """Run the Brand OS content-draft workflow from an MCP client."""
        from brand_os.workflows.content_draft import build_content_draft

        return build_content_draft(request)

    @server.tool()
    def interview_os_brief(request: InterviewBriefRequest) -> InterviewBriefResponse:
        """Run the Interview OS brief workflow from an MCP client."""
        from interview_os.workflows.interview_brief import build_interview_brief

        return build_interview_brief(request)

    @server.tool()
    def one_on_one_os_brief(request: OneOnOneRequest) -> OneOnOneResponse:
        """Run the One-on-One OS meeting brief workflow from an MCP client."""
        from one_on_one_os.workflows.meeting_brief import build_meeting_brief

        return build_meeting_brief(request)

    return server


def main() -> None:
    """Run the standalone MCP server over stdio for Claude Desktop or Claude Code."""
    create_server().run("stdio")


if __name__ == "__main__":
    main()
