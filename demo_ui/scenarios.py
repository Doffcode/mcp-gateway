"""Gateway Studio scene drivers. Every scene runs the REAL gateway (`gateway.cli run` over stdio, the same way
scripts/demo1_rugpull.py and scripts/demo2_mismatch.py do) and returns what happened: tool lists, the gateway's
JSON log records, hashes and diffs. The browser only animates these results; nothing here is simulated.
"""

import asyncio
import csv
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters

from gateway import cli as gateway_cli
from gateway.canonical import canonical_json, pretty, tool_hash, tool_view
from gateway.l2_capability import L2Analyzer

ROOT = Path(__file__).resolve().parents[1]
SERVERS = ROOT / "fixtures" / "servers"
TAXONOMY = ROOT / "taxonomy"
STUDIO_VAR = ROOT / "var" / "studio"

_l2 = L2Analyzer.from_dir(TAXONOMY)


def _gateway_params(work: Path, name: str, fixture: list[str], env: dict | None = None) -> StdioServerParameters:
    cfg = work / "gateway.yaml"
    cfg.write_text(f"k: 2\npin_store: {work / 'pins.json'}\nlog_file: {work / 'gateway.log'}\n"
                   f"taxonomy_dir: {TAXONOMY}\n")
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "gateway.cli", "--config", str(cfg), "run", "--name", name, "--",
              sys.executable, str(SERVERS / fixture[0]), *fixture[1:]],
        env={**os.environ, "GATEWAY_VAR": str(work), **(env or {})})


def _direct_params(fixture: list[str], work: Path) -> StdioServerParameters:
    return StdioServerParameters(command=sys.executable, args=[str(SERVERS / fixture[0]), *fixture[1:]],
                                 env={**os.environ, "GATEWAY_VAR": str(work)})


def _read_log(work: Path, start: int = 0) -> list[dict]:
    log = work / "gateway.log"
    if not log.exists():
        return []
    return [json.loads(x) for x in log.read_text().splitlines()[start:] if x.strip()]


def _log_len(work: Path) -> int:
    log = work / "gateway.log"
    return len(log.read_text().splitlines()) if log.exists() else 0


def tool_card(tool) -> dict:
    """Everything the UI shows about one tool: the pinned view, its canonical JSON and SHA-256, and L2's analysis."""
    v = tool_view(tool)
    implied = {c: {"action": a, "target": t, "target_pattern": p.text, "source": p.source, "evidence": ev}
               for c, (a, p, t, ev) in _l2.implied(v).items()}
    declared = sorted(_l2.declared(v))
    return {"name": v["name"], "description": v["description"],
            "params": {k: (s or {}).get("type", "") for k, s in (v["inputSchema"].get("properties") or {}).items()},
            "canonical": canonical_json(v), "hash": tool_hash(v), "implied": implied, "declared": declared,
            "flags": [f.as_dict() for f in _l2(v)]}


async def _list_via(params: StdioServerParameters) -> list[dict]:
    async with Client(params, cache=None) as c:
        return [tool_card(t) for t in (await c.list_tools()).tools]


async def mcp_basics() -> dict:
    """Scene 1: what an agent receives from two ordinary servers (clean weather + filesystem), no gateway."""
    work = Path(tempfile.mkdtemp(prefix="studio-basics-"))
    weather = await _list_via(_direct_params(["weather.py", "--variant", "clean"], work))
    fs = await _list_via(_direct_params(["filesystem.py"], work))
    return {"servers": {"weather": weather, "filesystem": fs}}


async def l2_scene() -> dict:
    """Scene 3: the poisoned weather server listed directly vs through the gateway."""
    work = Path(tempfile.mkdtemp(prefix="studio-l2-"))
    raw = await _list_via(_direct_params(["weather.py", "--variant", "poisoned"], work))
    served = await _list_via(_gateway_params(work, "weather", ["weather.py", "--variant", "poisoned"]))
    return {"upstream": raw, "served": [t["name"] for t in served], "log": _read_log(work)}


class RugpullSession:
    """Scene 4: one pin store that persists across steps; the fixture's description is switched by a control file."""

    TOOL = "convert_currency"

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> dict:
        self.work = Path(tempfile.mkdtemp(prefix="studio-rugpull-"))
        self.control = self.work / "rugpull_mode"
        self.control.write_text("clean")
        return {"mode": "clean"}

    async def list(self, mode: str | None = None) -> dict:
        if mode:
            self.control.write_text(mode)
        start = _log_len(self.work)
        params = _gateway_params(self.work, "rugpull", ["rugpull.py"], env={"RUGPULL_CONTROL": str(self.control)})
        upstream = await _list_via(StdioServerParameters(
            command=sys.executable, args=[str(SERVERS / "rugpull.py")],
            env={**os.environ, "RUGPULL_CONTROL": str(self.control)}))
        served = await _list_via(params)
        pins = json.loads((self.work / "pins.json").read_text())
        pin = pins["pins"].get(f"rugpull/{self.TOOL}", {})
        return {"mode": self.control.read_text().strip(), "upstream": upstream,
                "served": [t["name"] for t in served], "pinned_hash": pin.get("hash"),
                "pinned_pretty": pretty(json.loads(pin["canonical"])) if pin else "",
                "log": _read_log(self.work, start)}

    def cli(self, command: str) -> dict:
        """The presenter types a real `gateway pin ...` command; only `pin approve rugpull <tool>` and `pin list` run."""
        import contextlib
        import io
        import shlex

        argv = shlex.split(command)
        if argv[:1] == ["gateway"]:
            argv = argv[1:]
        if not (argv[:2] == ["pin", "list"] or (argv[:2] == ["pin", "approve"] and len(argv) == 4)):
            return {"ok": False, "output": "only `gateway pin approve <server> <tool>` and `gateway pin list` are allowed here"}
        start = _log_len(self.work)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = gateway_cli.main(["--config", str(self.work / "gateway.yaml"), *argv])
        return {"ok": rc == 0, "output": (out.getvalue() + err.getvalue()).strip(), "log": _read_log(self.work, start)}

    def approve(self) -> dict:
        start = _log_len(self.work)
        rc = gateway_cli.main(["--config", str(self.work / "gateway.yaml"), "pin", "approve", "rugpull", self.TOOL])
        return {"ok": rc == 0, "log": _read_log(self.work, start)}


def check_description(name: str, description: str, params: dict[str, str]) -> dict:
    """Scene 6, "try to poison it": L2 on a tool typed in by the audience. Same analyzer the gateway uses."""
    tool = {"name": name or "custom_tool", "description": description,
            "inputSchema": {"type": "object", "properties": {k: {"type": v or "string"} for k, v in params.items()}}}
    card = tool_card(tool)
    return {**card, "verdict": "removed" if card["flags"] else "allowed"}


RECORDINGS = ROOT / "recordings" / "demo3" / "transcripts"


async def agent_replay(gateway: bool, seed: int, queue: asyncio.Queue) -> None:
    """Scene 2, recorded mode: replays a REAL transcript recorded on the lab PC (qwen3:8b, GPU), clearly labelled.
    The weather server's received calls are the transcript's own get_weather/get_forecast tool calls."""
    from agent.loop import CANARY

    f = RECORDINGS / f"{'on' if gateway else 'off'}_seed{seed % 10}.json"
    t = json.loads(f.read_text())
    await queue.put({"kind": "start", "model": t["model"], "seed": t["seed"], "gateway": gateway, "recorded": True,
                     "source": f"recordings/demo3/transcripts/{f.name}"})
    calls = []
    for ev in t["events"]:
        if ev["kind"] == "tools" and gateway:
            for r in t.get("gateway_log", []):
                await queue.put({"kind": "gateway", **r})
        await asyncio.sleep(float(os.environ.get("STUDIO_REPLAY_DELAY", "0.9")))
        await queue.put(ev)
        if ev["kind"] == "tool_call" and ev.get("tool") in ("get_weather", "get_forecast"):
            calls.append(json.dumps({"args": ev.get("args", {}), "tool": ev["tool"]}, sort_keys=True))
    await queue.put({"kind": "server_log", "lines": calls})
    await queue.put({"kind": "done", "leaked": t["leaked"], "canary": CANARY})


async def agent_run(gateway: bool, seed: int, queue: asyncio.Queue, prompt: str | None = None) -> None:
    """Scene 2: the real local-model agent (agent/loop.py), streaming events as they happen."""
    from agent import loop

    run_dir = STUDIO_VAR / f"agent_{'on' if gateway else 'off'}_seed{seed}"
    cfg = loop.local_cfg()
    await queue.put({"kind": "start", "model": cfg["model"], "seed": seed, "gateway": gateway,
                     "device": "cpu" if cfg.get("num_gpu") == 0 else "default"})
    sent_log = 0

    def on_event(ev: dict) -> None:
        nonlocal sent_log
        queue.put_nowait({**ev})
        if ev["kind"] == "tools":  # the gateway has filtered tools/list by now: show its log first
            recs = _read_log(run_dir)
            for r in recs[sent_log:]:
                queue.put_nowait({"kind": "gateway", **r})
            sent_log = len(recs)

    try:
        t = await loop.run_once(gateway, seed, False, run_dir, verbose=False, on_event=on_event,
                                prompt=prompt or loop.PROMPT)
        for r in _read_log(run_dir)[sent_log:]:
            await queue.put({"kind": "gateway", **r})
        calls = run_dir / "weather_calls.jsonl"
        await queue.put({"kind": "server_log", "lines": calls.read_text().splitlines() if calls.exists() else []})
        await queue.put({"kind": "done", "leaked": t["leaked"], "canary": loop.CANARY})
    except Exception as e:  # surfaced to the presenter, never hidden
        await queue.put({"kind": "error", "text": f"{type(e).__name__}: {e}"})


def load_results() -> list[dict]:
    with open(ROOT / "results" / "results.csv") as f:
        return list(csv.DictReader(f))


def cleanup_tmp() -> None:
    shutil.rmtree(STUDIO_VAR, ignore_errors=True)
