"""Gateway Lab session: real server processes, the real gateway proxy, and a tap on every stdio hop.

With the gateway:     agent -> tap(agent-gw) -> gateway run -> tap(gw-server) -> server
Without the gateway:  agent -> tap(agent-server) -> server
The UI shows exactly what the taps and the gateway log recorded; nothing is synthesised.
"""

import json
import os
import sys
import tempfile
import time
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters

from .scenarios import ROOT, SERVERS, TAXONOMY, tool_card

PY = sys.executable
OFFICIAL_VERSION = "2026.10.10"  # pinned versions of the official reference servers (run locally via uvx)


def server_cmd(kind: str, opts: dict) -> list[str]:
    if kind == "weather":
        return [PY, str(SERVERS / "weather.py"), "--variant", opts.get("variant", "poisoned")]
    if kind == "filesystem":
        return [PY, str(SERVERS / "filesystem.py")]
    if kind == "mcptox":
        cmd = [PY, str(SERVERS / "mcptox_server.py"), "--server", opts["server"]]
        return cmd + (["--case", opts["case"]] if opts.get("case") else [])
    if kind == "git":  # official mcp-server-git, read-only use, pointed at this project's own repository
        return ["uvx", f"mcp-server-git=={OFFICIAL_VERSION}", "--repository", str(ROOT)]
    if kind == "time":
        return ["uvx", f"mcp-server-time=={OFFICIAL_VERSION}", "--local-timezone", "Asia/Kolkata"]
    raise ValueError(f"unknown server kind {kind}")


def server_name(kind: str, opts: dict) -> str:
    return opts["server"] if kind == "mcptox" else kind


class LabSession:
    def __init__(self) -> None:
        self.clients: dict[str, Client] = {}
        self.info: dict[str, dict] = {}
        self.work = Path(tempfile.mkdtemp(prefix="lab-"))
        self.wire = self.work / "wire.jsonl"
        self.gwlog = self.work / "gateway.log"
        self.cfg = self.work / "gateway.yaml"
        self.cfg.write_text(f"k: 2\npin_store: {self.work / 'pins.json'}\nlog_file: {self.gwlog}\ntaxonomy_dir: {TAXONOMY}\n")
        self.gateway = True

    def _tap(self, hop: str, cmd: list[str]) -> list[str]:
        return [PY, "-m", "demo_ui.tap", "--hop", hop, "--log", str(self.wire), "--", *cmd]

    def params(self, name: str, cmd: list[str]) -> StdioServerParameters:
        if self.gateway:
            inner = [PY, "-m", "gateway.cli", "--config", str(self.cfg), "run", "--name", name, "--",
                     *self._tap(f"gw→{name}", cmd)]
            full = self._tap(f"agent→gw[{name}]", inner)
        else:
            full = self._tap(f"agent→{name}", cmd)
        return StdioServerParameters(command=full[0], args=full[1:], cwd=str(ROOT),
                                     env={**os.environ, "GATEWAY_VAR": str(self.work), "PYTHONPATH": str(ROOT)})

    async def connect(self, servers: list[dict], gateway: bool) -> dict:
        await self.disconnect()
        self.gateway = gateway
        for s in servers:
            kind, opts = s["kind"], s.get("opts", {})
            name = server_name(kind, opts)
            cmd = server_cmd(kind, opts)
            c = Client(self.params(name, cmd), cache=None)
            t0 = time.perf_counter()
            await c.__aenter__()
            self.clients[name] = c
            self.info[name] = {"kind": kind, "opts": opts, "cmd": cmd, "connect_ms": round((time.perf_counter() - t0) * 1000)}
        return await self.list_all()

    async def list_all(self) -> dict:
        out = {}
        for name, c in self.clients.items():
            mark = self._len(self.gwlog)
            t0 = time.perf_counter()
            served = (await c.list_tools()).tools
            ms = (time.perf_counter() - t0) * 1000
            log = self._read(self.gwlog, mark)
            upstream = self._last_upstream_tools(name) if self.gateway else [t.model_dump(mode="json", by_alias=True) for t in served]
            removed = {r["tool"]: r["reason"] for r in log if r.get("event") == "removed" and r.get("server") == name}
            out[name] = {**self.info[name], "gateway": self.gateway, "roundtrip_ms": round(ms, 1),
                         "upstream": [tool_card(t) for t in upstream], "served": [t.name for t in served],
                         "removed": removed, "check_ms": next((r.get("check_ms") for r in log if r.get("event") == "tools_list"
                                                                 and r.get("server") == name), None)}
        return {"servers": out, "procs": self.procs()}

    async def call(self, server: str, tool: str, args: dict) -> dict:
        r = await self.clients[server].call_tool(tool, args)
        return {"is_error": bool(r.is_error), "text": "\n".join(getattr(x, "text", "") for x in r.content)}

    async def disconnect(self) -> None:
        for c in reversed(list(self.clients.values())):
            try:
                await c.__aexit__(None, None, None)
            except Exception:
                pass
        self.clients.clear()
        self.info.clear()

    def procs(self) -> list[dict]:
        return [r for r in self._read(self.wire) if "proc" in r]

    def _last_upstream_tools(self, name: str) -> list[dict]:
        """The tools/list result exactly as the real server sent it to the gateway (taken from the tap)."""
        hop = f"gw→{name}"
        for r in reversed(self._read(self.wire)):
            m = r.get("msg")
            if r.get("hop") == hop and r.get("dir") == "res" and isinstance(m, dict) and "tools" in (m.get("result") or {}):
                return m["result"]["tools"]
        return []

    @staticmethod
    def _len(p: Path) -> int:
        return len(p.read_text().splitlines()) if p.exists() else 0

    @staticmethod
    def _read(p: Path, start: int = 0) -> list[dict]:
        if not p.exists():
            return []
        return [json.loads(x) for x in p.read_text().splitlines()[start:] if x.strip()]


async def chat(lab: LabSession, prompt: str, seed: int = 0):
    """The agent: an Ollama tool-calling loop over whatever servers are connected in the lab (same loop shape as
    agent/loop.py). Yields events as they happen; every tool call goes over the tapped stdio hops."""
    import ollama

    from agent.loop import SYSTEM, local_cfg

    cfg = local_cfg()
    llm = ollama.AsyncClient(host=cfg["ollama_host"])
    owner, tools = {}, []
    for name, c in lab.clients.items():
        for t in (await c.list_tools()).tools:
            owner[t.name] = name
            tools.append({"type": "function", "function": {"name": t.name, "description": t.description or "",
                                                          "parameters": t.input_schema}})
    yield {"kind": "tools", "served": sorted(owner), "model": cfg["model"]}
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]
    opts = {"temperature": 0.7, "seed": seed, "num_ctx": cfg["num_ctx"]}
    opts.update({k: cfg[k] for k in ("num_predict", "num_gpu") if cfg[k] is not None})
    for _ in range(6):
        t0 = time.perf_counter()
        r = await llm.chat(model=cfg["model"], messages=messages, tools=tools, think=False, options=opts)
        messages.append(r.message)
        if not r.message.tool_calls:
            yield {"kind": "assistant", "text": (r.message.content or "").strip(), "ms": round((time.perf_counter() - t0) * 1000)}
            return
        for tc in r.message.tool_calls:
            name, args = tc.function.name, dict(tc.function.arguments or {})
            yield {"kind": "tool_call", "tool": name, "server": owner.get(name), "args": args}
            if name in owner:
                res = await lab.call(owner[name], name, args)
                text = res["text"]
            else:
                text = f"error: unknown tool {name}"
            yield {"kind": "tool_result", "tool": name, "text": text[:1200]}
            messages.append({"role": "tool", "content": text, "tool_name": name})
    yield {"kind": "assistant", "text": "(stopped after 6 rounds)"}
