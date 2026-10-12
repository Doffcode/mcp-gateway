"""Demo 1: rug-pull caught by L1. Drives the real `gateway run` proxy over stdio as an agent would."""

import json
import sys
import tempfile
from pathlib import Path

import anyio
from mcp import Client
from mcp.client.stdio import StdioServerParameters

ROOT = Path(__file__).resolve().parents[1]


def banner(s: str) -> None:
    print(f"\n=== {s} ===")


async def main() -> None:
    work = Path(tempfile.mkdtemp(prefix="demo1-"))
    control, log = work / "rugpull_mode", work / "gateway.log"
    cfg = work / "gateway.yaml"
    cfg.write_text(f"k: 2\npin_store: {work / 'pins.json'}\nlog_file: {log}\n")
    control.write_text("clean")
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "gateway.cli", "--config", str(cfg), "run", "--name", "rugpull", "--",
              sys.executable, str(ROOT / "fixtures/servers/rugpull.py")],
        env={"RUGPULL_CONTROL": str(control), "PATH": "/usr/bin:/bin"},
    )
    async with Client(params, cache=None) as agent:
        banner("1. server serves a clean description; gateway pins it (TOFU)")
        tools = (await agent.list_tools()).tools
        print("agent sees:", [t.name for t in tools])
        print("description:", tools[0].description)

        banner("2. server silently changes its description (control file -> evil)")
        control.write_text("evil")
        tools = (await agent.list_tools()).tools
        print("agent sees:", [t.name for t in tools])

        r = await agent.call_tool("convert_currency", {"amount": 1, "from_currency": "USD", "to_currency": "INR"})
        print("call attempt:", r.content[0].text)

    banner("gateway log (removals + diff)")
    for line in log.read_text().splitlines():
        rec = json.loads(line)
        if rec["event"] == "l1_mismatch":
            print(f"L1 MISMATCH {rec['server']}/{rec['tool']}  {rec['old_hash'][:12]} -> {rec['new_hash'][:12]}")
            print(rec["diff"])
        elif rec["event"] in ("removed", "quarantine"):
            print(f"[{rec['event']}] {rec['reason']}")
    print(f"\nfull JSON log: {log}")


anyio.run(main)
