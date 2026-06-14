import asyncio

from apps.mcp.server import create_server


def test_mcp_server_registers_expected_tools() -> None:
    server = create_server()

    async def _run() -> None:
        tools = await server.list_tools()
        names = {tool.name for tool in tools}
        assert names == {
            "director_os_weekly_update",
            "brand_os_content_draft",
            "interview_os_brief",
            "one_on_one_os_brief",
        }

    asyncio.run(_run())


def test_mcp_tool_schemas_reflect_pydantic_request_models() -> None:
    server = create_server()

    async def _run() -> None:
        tools = await server.list_tools()
        by_name = {tool.name: tool for tool in tools}

        director_schema = by_name["director_os_weekly_update"].inputSchema
        brand_schema = by_name["brand_os_content_draft"].inputSchema

        assert director_schema["type"] == "object"
        assert "request" in director_schema["properties"]
        assert director_schema["properties"]["request"]["$ref"] == "#/$defs/WeeklyUpdateRequest"

        assert brand_schema["type"] == "object"
        assert "request" in brand_schema["properties"]
        assert brand_schema["properties"]["request"]["$ref"] == "#/$defs/BrandContentDraftRequest"

    asyncio.run(_run())


def test_mcp_tools_execute_using_existing_workflows() -> None:
    server = create_server()

    async def _run() -> None:
        result = await server.call_tool(
            "director_os_weekly_update",
            {
                "request": {
                    "data_path": "data/local_only/projects",
                    "focus": "leadership update",
                    "max_documents": 2,
                }
            },
        )

        payload = result[1] if isinstance(result, tuple) else result
        if isinstance(payload, list):
            payload = payload[-1]

        assert isinstance(payload, dict)
        assert "summary" in payload
        assert "wins" in payload

    asyncio.run(_run())
