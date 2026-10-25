from __future__ import annotations

import inspect

from mcp.server.fastmcp import FastMCP

from packages.shared.domains import DOMAINS, DomainSpec

# Importing the registry loads only Pydantic schemas. Each domain spec imports
# its workflow — and with it LangGraph, LangChain, LangSmith, and ChromaDB — on
# first call. On a cold start those imports can take longer than an MCP
# client's connect timeout (30s in Claude Code), so deferring them lets the
# server answer `initialize` and `tools/list` immediately.


def _make_tool(spec: DomainSpec):
    """Build the MCP tool function for one registered domain."""

    def run_domain_workflow(request):
        return spec.run(request)

    # FastMCP derives the tool's input and output schemas from the signature,
    # so give the shared handler this domain's concrete request/response types.
    run_domain_workflow.__signature__ = inspect.Signature(
        parameters=[
            inspect.Parameter(
                "request",
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=spec.request_model,
            )
        ],
        return_annotation=spec.response_model,
    )
    run_domain_workflow.__annotations__ = {
        "request": spec.request_model,
        "return": spec.response_model,
    }
    return run_domain_workflow


def create_server() -> FastMCP:
    """Create the standalone MCP server exposing every registered domain as a tool."""
    server = FastMCP("ai-operating-system")
    for spec in DOMAINS.values():
        server.add_tool(
            _make_tool(spec),
            name=spec.tool.name,
            description=spec.tool.description,
        )
    return server


def main() -> None:
    """Run the standalone MCP server over stdio for Claude Desktop or Claude Code."""
    create_server().run("stdio")


if __name__ == "__main__":
    main()
