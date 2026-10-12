"""Legitimate filesystem fixture: read_file(path), confined to the sandbox directory."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import SANDBOX  # noqa: E402

from mcp.server.mcpserver import MCPServer  # noqa: E402

mcp = MCPServer("filesystem")


@mcp.tool(description="Read the complete contents of a text file inside the sandbox directory.")
def read_file(path: str) -> str:
    p = Path(path)
    p = (p if p.is_absolute() else SANDBOX / p).resolve()
    if not p.is_relative_to(SANDBOX):
        return f"error: {path} is outside the sandbox"
    return p.read_text()


if __name__ == "__main__":
    mcp.run()
