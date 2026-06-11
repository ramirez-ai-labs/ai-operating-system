"""
Filesystem MCP server for AI-OS.

Exposes local project and brand data as MCP tools so the Chief of Staff
orchestrator can retrieve grounded context via the standard tool_use interface
rather than direct file reads.

Starting the server (standalone):
    python -m packages.shared.mcp.filesystem_server

Using in tests or the orchestrator:
    from packages.shared.mcp.filesystem_server import FilesystemMCPServer
    server = FilesystemMCPServer(root_path="data/local_only")
    result = server.call_tool("read_file", {"path": "projects/status.md"})

MCP tool definitions (pass to ClaudeProvider.complete(tools=...)):
    from packages.shared.mcp.filesystem_server import get_tool_definitions
    tools = get_tool_definitions()
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def get_tool_definitions() -> list[dict[str, Any]]:
    """
    Return MCP tool definitions in Anthropic tool_use schema format.

    These are passed to ClaudeProvider.complete(tools=...) so Claude can
    invoke filesystem operations as part of workflow synthesis.
    """
    return [
        {
            "name": "list_files",
            "description": (
                "List files and directories at a given path within the "
                "AI-OS data directory. Use this to discover what project "
                "notes, roadmap docs, or brand materials are available "
                "before deciding which to read."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "Relative path within the data directory. "
                            "Example: 'projects' or 'projects/q2-roadmap'"
                        ),
                    },
                    "pattern": {
                        "type": "string",
                        "description": (
                            "Optional glob pattern to filter results. "
                            "Example: '*.md' to list only markdown files."
                        ),
                    },
                },
                "required": ["path"],
            },
        },
        {
            "name": "read_file",
            "description": (
                "Read the full contents of a file within the AI-OS data "
                "directory. Use this to retrieve project notes, meeting "
                "summaries, roadmap documents, or brand materials for "
                "synthesis. Prefer reading specific files over listing "
                "directories when the file path is already known."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "Relative path to the file within the data directory. "
                            "Example: 'projects/weekly-notes.md'"
                        ),
                    },
                },
                "required": ["path"],
            },
        },
        {
            "name": "search_content",
            "description": (
                "Search file contents for a keyword or phrase within a "
                "directory. Returns matching file paths and the lines "
                "containing the match. Use this when you need to find "
                "documents that mention a specific topic, risk, or team "
                "member without reading every file individually."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "Directory to search within. "
                            "Example: 'projects' or 'brand'"
                        ),
                    },
                    "query": {
                        "type": "string",
                        "description": (
                            "Search term or phrase. Case-insensitive. "
                            "Example: 'blocker' or 'Q3 launch'"
                        ),
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of matching lines to return. Default: 20.",
                        "default": 20,
                    },
                },
                "required": ["path", "query"],
            },
        },
    ]


class FilesystemMCPServer:
    """
    MCP server exposing local filesystem tools to the AI-OS orchestrator.

    Security model:
    - All paths are resolved relative to `root_path` (default: data/local_only)
    - Path traversal attempts (../) are blocked via resolved-path check
    - Read-only: no write tools are exposed
    - File size capped at MAX_FILE_BYTES to prevent context window overflow

    Enterprise deployment note (see docs/DEPLOYMENT.md):
        In a customer environment, replace the local root_path with a
        network share, S3 bucket adapter, or SharePoint connector.
        The tool interface is identical — only the storage backend changes.
    """

    MAX_FILE_BYTES = 50_000   # ~12k tokens — stays within context budget
    MAX_SEARCH_FILES = 100    # cap directory traversal for large repos

    def __init__(self, root_path: str | Path = "data/local_only") -> None:
        self.root = Path(root_path).resolve()
        logger.info("FilesystemMCPServer root: %s", self.root)

    def call_tool(self, name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
        """
        Dispatch a tool call by name.

        Returns a dict with:
            success: bool
            result:  str   (tool output for Claude's tool_result block)
            error:   str | None
        """
        handlers = {
            "list_files": self._list_files,
            "read_file": self._read_file,
            "search_content": self._search_content,
        }

        if name not in handlers:
            return {
                "success": False,
                "result": "",
                "error": f"Unknown tool: {name}. Available: {list(handlers)}",
            }

        try:
            result = handlers[name](**tool_input)
            return {"success": True, "result": result, "error": None}
        except ValueError as exc:
            logger.warning("MCP tool %s input error: %s", name, exc)
            return {"success": False, "result": "", "error": str(exc)}
        except Exception as exc:
            logger.error("MCP tool %s unexpected error: %s", name, exc, exc_info=True)
            return {
                "success": False,
                "result": "",
                "error": f"Internal error in {name}. Check server logs.",
            }

    def _list_files(self, path: str, pattern: str = "*") -> str:
        target = self._safe_resolve(path)

        if not target.exists():
            raise ValueError(f"Path does not exist: {path}")
        if not target.is_dir():
            raise ValueError(f"Path is not a directory: {path}")

        matches = sorted(target.glob(pattern))
        if not matches:
            return f"No files matching '{pattern}' in {path}"

        lines: list[str] = [f"Files in {path} (pattern={pattern}):"]
        for item in matches:
            rel = item.relative_to(self.root)
            marker = "/" if item.is_dir() else ""
            size = f"  ({item.stat().st_size:,} bytes)" if item.is_file() else ""
            lines.append(f"  {rel}{marker}{size}")

        return "\n".join(lines)

    def _read_file(self, path: str) -> str:
        target = self._safe_resolve(path)

        if not target.exists():
            raise ValueError(f"File does not exist: {path}")
        if not target.is_file():
            raise ValueError(f"Path is not a file: {path}")

        size = target.stat().st_size
        if size > self.MAX_FILE_BYTES:
            raise ValueError(
                f"File too large to read: {size:,} bytes "
                f"(limit {self.MAX_FILE_BYTES:,}). "
                f"Use search_content to find specific sections instead."
            )

        try:
            content = target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raise ValueError(f"File is not valid UTF-8 text: {path}")

        return f"=== {path} ===\n{content}"

    def _search_content(
        self,
        path: str,
        query: str,
        max_results: int = 20,
    ) -> str:
        target = self._safe_resolve(path)

        if not target.exists():
            raise ValueError(f"Path does not exist: {path}")

        query_lower = query.lower()
        matches: list[str] = []
        files_searched = 0

        for file_path in sorted(target.rglob("*")):
            if not file_path.is_file():
                continue
            if files_searched >= self.MAX_SEARCH_FILES:
                matches.append(
                    f"[Search stopped after {self.MAX_SEARCH_FILES} files — "
                    "narrow the path or use a more specific query]"
                )
                break

            if file_path.stat().st_size > self.MAX_FILE_BYTES:
                continue

            try:
                text = file_path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue

            files_searched += 1
            rel = file_path.relative_to(self.root)

            for lineno, line in enumerate(text.splitlines(), start=1):
                if query_lower in line.lower():
                    matches.append(f"{rel}:{lineno}: {line.strip()}")
                    if len(matches) >= max_results:
                        break

            if len(matches) >= max_results:
                break

        if not matches:
            return f"No matches for '{query}' in {path} ({files_searched} files searched)"

        header = (
            f"Search results for '{query}' in {path} "
            f"({len(matches)} matches, {files_searched} files searched):"
        )
        return header + "\n" + "\n".join(matches)

    def _safe_resolve(self, rel_path: str) -> Path:
        """
        Resolve a relative path inside the server root.

        Raises ValueError if the resolved path escapes the root — this is the
        actual path traversal control. The startswith check on the resolved
        absolute path is authoritative.
        """
        resolved = (self.root / rel_path.lstrip("/")).resolve()

        if not str(resolved).startswith(str(self.root)):
            raise ValueError(
                f"Path traversal attempt blocked: '{rel_path}' "
                f"resolves outside server root."
            )

        return resolved


def build_tool_result_message(
    tool_call_id: str,
    result: dict[str, Any],
) -> dict[str, Any]:
    """
    Format a tool result for the Anthropic Messages API multi-turn format.

    The orchestrator calls this after executing each MCP tool, then appends
    the result to the message history before the next Claude call.

    Flow:
        1. Claude returns tool_call: {id: "tc_1", name: "read_file", input: {...}}
        2. Orchestrator calls FilesystemMCPServer.call_tool("read_file", input)
        3. Orchestrator calls build_tool_result_message("tc_1", server_result)
        4. Orchestrator appends {role: "user", content: [tool_result_block]}
        5. Orchestrator calls ClaudeProvider.complete(messages=updated_history)
    """
    content = result["result"] if result["success"] else f"Error: {result['error']}"

    return {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": tool_call_id,
                "content": content,
            }
        ],
    }


if __name__ == "__main__":
    import logging as _logging
    import sys
    _logging.basicConfig(level=_logging.INFO)

    root = sys.argv[1] if len(sys.argv) > 1 else "data/local_only"
    server = FilesystemMCPServer(root_path=root)

    print(f"\nFilesystem MCP server running against: {server.root}")
    print("Available tools:", [t["name"] for t in get_tool_definitions()])
    print("\nQuick smoke test — listing root:\n")

    result = server.call_tool("list_files", {"path": ""})
    print(result["result"] if result["success"] else f"Error: {result['error']}")
