"""`gateway` CLI.

  gateway run --name weather -- python fixtures/servers/weather.py --variant poisoned
  gateway pin approve <server> <tool>
  gateway pin list
"""

import argparse
import json
import os
import sys

import anyio
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from mcp.server.stdio import stdio_server

from . import config as config_mod
from .l1_pins import PinStore
from .logjson import JsonLog
from .proxy import Gateway


def upstream_params(cmd: list[str]) -> StdioServerParameters:
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        raise SystemExit("missing upstream command after --")
    # Upstream inherits the gateway's environment, as it would from a normal MCP host config.
    return StdioServerParameters(command=cmd[0], args=cmd[1:], env=dict(os.environ))


def make_l2(cfg):
    try:
        from .l2_capability import L2Analyzer
    except ImportError:  # L2 not built yet
        return None
    return L2Analyzer.from_dir(cfg.taxonomy_dir)


async def run_proxy(name: str, cmd: list[str], cfg) -> None:
    log = JsonLog(cfg.log_file)
    async with Client(upstream_params(cmd), cache=None) as upstream:
        l2 = make_l2(cfg)
        gw = Gateway(name, upstream, PinStore(cfg.pin_store), log, cfg.k, **({"l2": l2} if l2 else {}))
        server = gw.build_server()
        async with stdio_server() as (r, w):
            await server.run(r, w, server.create_initialization_options())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="gateway")
    ap.add_argument("--config", default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run the proxy on stdio in front of an upstream stdio server")
    r.add_argument("--name", required=True, help="server name used for pins and logs")
    r.add_argument("upstream", nargs=argparse.REMAINDER)
    p = sub.add_parser("pin")
    psub = p.add_subparsers(dest="pin_cmd", required=True)
    a = psub.add_parser("approve", help="explicitly accept the pending (changed) version of a tool")
    a.add_argument("server")
    a.add_argument("tool")
    psub.add_parser("list")
    args = ap.parse_args(argv)
    cfg = config_mod.load(args.config)

    if args.cmd == "run":
        anyio.run(run_proxy, args.name, args.upstream, cfg)
        return 0
    store = PinStore(cfg.pin_store)
    if args.pin_cmd == "approve":
        try:
            h = store.approve(args.server, args.tool)
        except KeyError as e:
            print(f"error: {e.args[0]}", file=sys.stderr)
            return 1
        JsonLog(cfg.log_file, stream=None).emit("pin_approved", server=args.server, tool=args.tool, hash=h)
        print(f"approved {args.server}/{args.tool} -> {h[:16]}…")
        return 0
    print(json.dumps({k: {n: v["hash"] for n, v in d.items()} for k, d in store.list().items()}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
