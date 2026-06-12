"""Edge case tests for FilesystemMCPServer not covered in test_claude_mcp.py."""

from pathlib import Path

import pytest

from packages.shared.mcp.filesystem_server import FilesystemMCPServer


@pytest.fixture()
def fs(tmp_path: Path) -> FilesystemMCPServer:
    """Server rooted at a temporary directory."""
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "notes.md").write_text("# Notes\n\nfoo bar baz", encoding="utf-8")
    (tmp_path / "readme.md").write_text("# Readme\n\nhello world", encoding="utf-8")
    return FilesystemMCPServer(root_path=tmp_path)


class TestListFilesEdgeCases:
    def test_list_files_on_file_returns_error(self, fs: FilesystemMCPServer) -> None:
        result = fs.call_tool("list_files", {"path": "readme.md"})
        assert result["success"] is False
        assert "not a directory" in result["error"]

    def test_list_files_no_matches_returns_message(self, fs: FilesystemMCPServer) -> None:
        result = fs.call_tool("list_files", {"path": "subdir", "pattern": "*.xyz"})
        assert result["success"] is True
        assert "No files matching" in result["result"]


class TestReadFileEdgeCases:
    def test_read_directory_as_file_returns_error(self, fs: FilesystemMCPServer) -> None:
        result = fs.call_tool("read_file", {"path": "subdir"})
        assert result["success"] is False
        assert "not a file" in result["error"]

    def test_read_file_too_large_returns_error(self, tmp_path: Path) -> None:
        oversized = tmp_path / "big.txt"
        oversized.write_bytes(b"x" * (FilesystemMCPServer.MAX_FILE_BYTES + 1))
        server = FilesystemMCPServer(root_path=tmp_path)
        result = server.call_tool("read_file", {"path": "big.txt"})
        assert result["success"] is False
        assert "too large" in result["error"]

    def test_read_binary_file_returns_error(self, tmp_path: Path) -> None:
        binary = tmp_path / "image.bin"
        binary.write_bytes(bytes(range(256)))
        server = FilesystemMCPServer(root_path=tmp_path)
        result = server.call_tool("read_file", {"path": "image.bin"})
        assert result["success"] is False
        assert "UTF-8" in result["error"]


class TestSearchContentEdgeCases:
    def test_search_nonexistent_path_returns_error(self, fs: FilesystemMCPServer) -> None:
        result = fs.call_tool("search_content", {"path": "missing", "query": "anything"})
        assert result["success"] is False
        assert "does not exist" in result["error"]

    def test_search_respects_max_results(self, tmp_path: Path) -> None:
        for i in range(10):
            (tmp_path / f"doc{i}.md").write_text("keyword here\n" * 5, encoding="utf-8")
        server = FilesystemMCPServer(root_path=tmp_path)
        result = server.call_tool(
            "search_content", {"path": "", "query": "keyword", "max_results": 3}
        )
        assert result["success"] is True
        # Skip the header line; count only match lines (contain a colon-separated file:line: prefix)
        match_lines = [l for l in result["result"].splitlines() if ":" in l and "keyword here" in l]
        assert len(match_lines) <= 3


class TestPathTraversalEdgeCases:
    def test_absolute_path_traversal_blocked(self, fs: FilesystemMCPServer) -> None:
        result = fs.call_tool("read_file", {"path": "/etc/passwd"})
        assert result["success"] is False

    def test_dotdot_traversal_blocked(self, fs: FilesystemMCPServer) -> None:
        result = fs.call_tool("read_file", {"path": "../../etc/passwd"})
        assert result["success"] is False

    def test_windows_absolute_path_blocked(self, fs: FilesystemMCPServer) -> None:
        result = fs.call_tool("read_file", {"path": "C:/Windows/system32/cmd.exe"})
        assert result["success"] is False


class TestUnexpectedExceptionHandling:
    def test_unexpected_exception_returns_internal_error(
        self, fs: FilesystemMCPServer, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def boom(**_kwargs):
            raise RuntimeError("disk failure")

        monkeypatch.setattr(fs, "_read_file", boom)
        result = fs.call_tool("read_file", {"path": "readme.md"})
        assert result["success"] is False
        assert "Internal error" in result["error"]
