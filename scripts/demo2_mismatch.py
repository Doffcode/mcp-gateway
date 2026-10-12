"""Demo 2: L2 capability mismatch. Drives the real `gateway run` proxy over stdio as an agent would."""

import json
import sys
import tempfile
from pathlib import Path

import anyio
from mcp import Client
from mcp.client.stdio import StdioServerParameters

ROOT = Path(__file__).resolve().parents[1]


async def main() -> None:
    work = Path(tempfile.mkdtemp(prefix="demo2-"))
    log = work / "gateway.log"
    cfg = work / "gateway.yaml"
    cfg.write_text(f"k: 2\npin_store: {work / 'pins.json'}\nlog_file: {log}\ntaxonomy_dir: {ROOT / 'taxonomy'}\n")
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "gateway.cli", "--config", str(cfg), "run", "--name", "weather", "--",
              sys.executable, str(ROOT / "fixtures/servers/weather.py"), "--variant", "poisoned"],
        env={"GATEWAY_VAR": str(work), "PATH": "/usr/bin:/bin"},
    )
    async with Client(params, cache=None) as agent:
        print("\n=== poisoned weather server: get_weather(city) description says to read a file ===")
        tools = (await agent.list_tools()).tools
        print("agent sees:", [t.name for t in tools])
        r = await agent.call_tool("get_forecast", {"city": "Chennai", "days": 2})
        print("get_forecast still works:", r.content[0].text)
        r = await agent.call_tool("get_weather", {"city": "Chennai"})
        print("get_weather call:", r.content[0].text)

    print("\n=== gateway log ===")
    for line in log.read_text().splitlines():
        rec = json.loads(line)
        if rec["event"] == "l2_flag":
            for f in rec["flags"]:
                print(f"L2 FLAG {rec['server']}/{rec['tool']} [{f['category']}] evidence: {f['evidence']!r}")
                print(f"        target pattern {f['target_pattern']!r} (source: {f['target_source']})")
        elif rec["event"] in ("removed", "quarantine"):
            print(f"[{rec['event']}] {rec['reason']}")
    print(f"\nfull JSON log: {log}")


anyio.run(main)
