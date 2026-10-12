"""Inline proxy: an MCP server to the agent and an MCP client to the real (upstream) server.

On every tools/list: fetch upstream (no client cache), run L1 -> L2 -> decision ladder per tool,
return only allowed tools, and log every removal with a one-sentence reason.
"""

import time
from collections.abc import Callable

import mcp_types as types
from mcp import Client
from mcp.server import Server

from .l1_pins import PinStore
from .ladder import Decision, decide
from .logjson import JsonLog

L2Fn = Callable[[types.Tool], list]


def _no_l2(tool: types.Tool) -> list:
    return []


class Gateway:
    def __init__(self, server_name: str, upstream: Client, pins: PinStore, log: JsonLog, k: int, l2: L2Fn = _no_l2):
        self.server_name = server_name
        self.upstream = upstream
        self.pins = pins
        self.log = log
        self.k = k
        self.l2 = l2
        self.decision: Decision | None = None

    async def filtered_tools(self) -> list[types.Tool]:
        listing = await self.upstream.list_tools(cache_mode="bypass")
        t0 = time.perf_counter()
        tools = {t.name: t for t in listing.tools}
        l1 = {n: self.pins.check(self.server_name, t) for n, t in tools.items()}
        l2 = {n: self.l2(t) for n, t in tools.items()}
        d = decide(self.server_name, list(tools), l1, l2, self.k)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        self.decision = d
        for n, res in l1.items():
            if res.status == "mismatch":
                self.log.emit("l1_mismatch", server=self.server_name, tool=n, old_hash=res.old_hash,
                              new_hash=res.new_hash, diff=res.diff)
            elif res.status == "new":
                self.log.emit("l1_pinned", server=self.server_name, tool=n, hash=res.new_hash)
        for n, flags in l2.items():
            if flags:
                self.log.emit("l2_flag", server=self.server_name, tool=n, flags=[f.as_dict() for f in flags])
        if d.quarantined:
            self.log.emit("quarantine", server=self.server_name, reason=d.quarantine_reason)
        for n, reason in d.removed.items():
            self.log.emit("removed", server=self.server_name, tool=n, reason=reason)
        self.log.emit("tools_list", server=self.server_name, served=d.allowed, removed=sorted(d.removed),
                      quarantined=d.quarantined, check_ms=round(elapsed_ms, 3))
        return [tools[n] for n in d.allowed]

    async def call_tool(self, name: str, arguments: dict | None) -> types.CallToolResult:
        if self.decision is None:
            await self.filtered_tools()
        d = self.decision
        if d.quarantined or name not in d.allowed:
            reason = d.removed.get(name, f"tool '{name}' is not in the gateway's approved list")
            self.log.emit("call_blocked", server=self.server_name, tool=name, reason=reason)
            return types.CallToolResult(content=[types.TextContent(type="text", text=f"Blocked by gateway: {reason}")],
                                        is_error=True)
        return await self.upstream.call_tool(name, arguments or {})

    def build_server(self) -> Server:
        async def on_list_tools(ctx, params) -> types.ListToolsResult:
            return types.ListToolsResult(tools=await self.filtered_tools())

        async def on_call_tool(ctx, params: types.CallToolRequestParams) -> types.CallToolResult:
            return await self.call_tool(params.name, params.arguments)

        return Server(f"gateway[{self.server_name}]", on_list_tools=on_list_tools, on_call_tool=on_call_tool)
