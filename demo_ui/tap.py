"""Stdio tap: run a command and copy its stdin/stdout unchanged, logging every JSON-RPC message that passes.

  python -m demo_ui.tap --hop gw-server --log wire.jsonl -- python fixtures/servers/weather.py

MCP stdio is newline-delimited JSON. Each message is appended to the log as
{"ts", "hop", "dir": "req"|"res" (towards the child | from the child), "size", "msg"}; the bytes forwarded are the
original bytes. The first record is {"proc": ...} with the child's PID and command line, so the UI can show it.
"""

import argparse
import asyncio
import json
import os
import sys
import time


def _write(log: str, rec: dict) -> None:
    with open(log, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _record(log: str, hop: str, direction: str, line: bytes) -> None:
    try:
        msg = json.loads(line)
    except ValueError:
        msg = line.decode("utf-8", "replace").rstrip("\n")
    _write(log, {"ts": time.time(), "hop": hop, "dir": direction, "size": len(line), "msg": msg})


async def main(hop: str, log: str, cmd: list[str]) -> int:
    child = await asyncio.create_subprocess_exec(*cmd, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                                                 stderr=None, limit=1 << 24)
    _write(log, {"ts": time.time(), "hop": hop, "proc": {"pid": child.pid, "tap_pid": os.getpid(), "cmd": cmd}})
    loop = asyncio.get_running_loop()
    reader = asyncio.StreamReader(limit=1 << 24)
    await loop.connect_read_pipe(lambda: asyncio.StreamReaderProtocol(reader), sys.stdin.buffer)
    out = sys.stdout.buffer

    async def upstream() -> None:  # our stdin -> child stdin
        while line := await reader.readline():
            child.stdin.write(line)
            await child.stdin.drain()
            _record(log, hop, "req", line)
        child.stdin.close()

    async def downstream() -> None:  # child stdout -> our stdout
        while line := await child.stdout.readline():
            out.write(line)
            out.flush()
            _record(log, hop, "res", line)

    up = asyncio.create_task(upstream())
    await downstream()
    up.cancel()
    return await child.wait()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--hop", required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument("cmd", nargs=argparse.REMAINDER)
    a = ap.parse_args()
    cmd = a.cmd[1:] if a.cmd[:1] == ["--"] else a.cmd
    sys.exit(asyncio.run(main(a.hop, a.log, cmd)))
