"""Score a real local MCP tool listing without calling or filtering tools."""

import argparse
import json
import sys
from pathlib import Path

import anyio
from mcp import Client
from mcp.client.stdio import StdioServerParameters

from gateway.l3 import Scorer

from .mcptox_ingest import ROOT


async def score(artifact, device, upstream):
    scorer = Scorer(artifact, device=device)
    async with Client(StdioServerParameters(command=upstream[0], args=upstream[1:]), cache=None) as client:
        listing = await client.list_tools(cache_mode="bypass")
    print(json.dumps({"model": scorer.kind, "results": scorer.score_listing(listing.tools)}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, default=ROOT / "var" / "l3")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("upstream", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    upstream = args.upstream[1:] if args.upstream[:1] == ["--"] else args.upstream
    if not upstream:
        parser.error("provide a local MCP server command after --")
    if upstream[0] == "python":
        upstream[0] = sys.executable
    anyio.run(score, args.artifact, args.device, upstream)


if __name__ == "__main__":
    main()
