"""MCPTox replay server: a real MCP stdio server that serves one MCPTox server's tool metadata, as released.

  python fixtures/servers/mcptox_server.py --server Gitlab                 # the 353-tool benchmark's authentic tools
  python fixtures/servers/mcptox_server.py --server Gitlab --case Gitlab#23  # + that case's poisoned tool

Tool metadata comes unchanged from data/raw/response_all.json via eval/mcptox_ingest.py (MCPTox ships it as prompt
text; parameter types are not in the source). Tool calls do NOT reach the real service: they return a marked stub and
are recorded in $GATEWAY_VAR/mcptox_calls.jsonl, because the MCPTox attack is about which call the model makes.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import VAR  # noqa: E402

import anyio  # noqa: E402
import mcp_types as types  # noqa: E402
from mcp.server import Server  # noqa: E402
from mcp.server.stdio import stdio_server  # noqa: E402

from eval.mcptox_ingest import load  # noqa: E402


def tools_for(server: str, case: str | None) -> list[dict]:
    s = load()["servers"][server]
    tools = list(s["authentic_tools"])
    if case:
        tools.append(next(c for c in s["cases"] if c["id"] == case)["poisoned_tool"])
    return tools


def build(server: str, case: str | None) -> Server:
    tools = tools_for(server, case)

    async def list_tools(ctx, params) -> types.ListToolsResult:
        return types.ListToolsResult(tools=[types.Tool(name=t["name"], description=t["description"],
                                                       input_schema=t["inputSchema"]) for t in tools])

    async def call_tool(ctx, params: types.CallToolRequestParams) -> types.CallToolResult:
        VAR.mkdir(parents=True, exist_ok=True)
        with open(VAR / "mcptox_calls.jsonl", "a") as f:
            f.write(json.dumps({"server": server, "tool": params.name, "args": params.arguments or {}}) + "\n")
        text = f"[MCPTox replay] {server}.{params.name} recorded; the real {server} API is not called."
        return types.CallToolResult(content=[types.TextContent(type="text", text=text)])

    return Server(f"mcptox-{server}", on_list_tools=list_tools, on_call_tool=call_tool)


async def main(server: str, case: str | None) -> None:
    srv = build(server, case)
    async with stdio_server() as (r, w):
        await srv.run(r, w, srv.create_initialization_options())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", required=True)
    ap.add_argument("--case")
    a = ap.parse_args()
    anyio.run(main, a.server, a.case)
