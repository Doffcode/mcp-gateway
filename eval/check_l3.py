"""Run a schema shortcut diagnostic and check L3 on genuine local MCP listings."""

import argparse
import json
import shutil
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import anyio
import numpy as np
from mcp import Client
from mcp.client.stdio import StdioServerParameters

from gateway.l3 import Scorer

from .l3_data import examples
from .mcptox_ingest import ROOT, load
from .split import load_split
from .train_l3 import results


def shortcut(scorer):
    rows = examples(load()["servers"], load_split()["heldout_servers"], scorer.manifest["k"])
    scores = np.array([
        not json.loads(row.text.rsplit("\nSchema: ", 1)[1]).get("properties")
        for row in rows
    ], dtype=float)
    return results(rows, scores, 0.5)


async def local_listings(scorer, node, package_dir):
    with TemporaryDirectory(prefix="l3-utility-") as directory:
        local = Path(directory)
        package_dir = package_dir.resolve()
        files = package_dir / "@modelcontextprotocol"

        def npm_command(package, *args):
            return [node, str(package / "dist" / "index.js"), *args]

        sources = {
            "outside_benchmark": {
                "time@2026.10.10": ["uvx", "--offline", "--python", "3.13", "mcp-server-time==2026.10.10"],
                "playwright@0.0.86": [node, str(package_dir / "@playwright/mcp/cli.js"), "--isolated"],
            },
            "owned_fixtures": {
                "weather-clean": [sys.executable, str(ROOT / "fixtures/servers/weather.py"), "--variant", "clean"],
                "benign": [sys.executable, str(ROOT / "fixtures/servers/benign.py")],
                "filesystem-fixture": [sys.executable, str(ROOT / "fixtures/servers/filesystem.py")],
            },
            "server_family_in_benchmark": {
                "git@2026.10.10": ["uvx", "--offline", "--python", "3.13", "mcp-server-git==2026.10.10", "--repository", str(ROOT)],
                "filesystem@2.4.0": npm_command(files / "server-filesystem", directory),
                "memory@2.2.1": npm_command(files / "server-memory"),
            },
        }
        output = {}
        for group, servers in sources.items():
            listings = {}
            for name, command in servers.items():
                params = StdioServerParameters(command=command[0], args=command[1:], cwd=directory,
                                               env={"MEMORY_FILE_PATH": str(local / "memory.jsonl")})
                async with Client(params, cache=None, mode="legacy") as client:
                    listing = await client.list_tools(cache_mode="bypass")
                verdicts = scorer.score_listing(listing.tools)
                for tool, verdict in zip(listing.tools, verdicts, strict=True):
                    verdict["no_parameter_properties"] = not tool.input_schema.get("properties")
                    verdict["no_required_parameters"] = not tool.input_schema.get("required")
                listings[name] = verdicts
            verdicts = [row for rows in listings.values() for row in rows]
            flagged = [row for row in verdicts if row["verdict"] == "flagged"]
            output[group] = {
                "tools": len(verdicts),
                "flagged_tools": len(flagged),
                "servers": len(listings),
                "servers_with_flags": sum(any(row["verdict"] == "flagged" for row in rows)
                                          for rows in listings.values()),
                "tools_with_no_parameter_properties": sum(row["no_parameter_properties"] for row in verdicts),
                "flags_with_no_parameter_properties": sum(row["no_parameter_properties"] for row in flagged),
                "tools_with_no_required_parameters": sum(row["no_required_parameters"] for row in verdicts),
                "flags_with_no_required_parameters": sum(row["no_required_parameters"] for row in flagged),
                "listings": listings,
            }
        return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, default=ROOT / "var/l3")
    parser.add_argument("--node", default=shutil.which("node"))
    parser.add_argument("--node-modules", type=Path, default=ROOT / "var/l3-utility-servers/node_modules")
    args = parser.parse_args()
    if not args.node:
        parser.error("provide a Node.js executable with --node")
    scorer = Scorer(args.artifact)
    print(json.dumps({
        "frozen_threshold": scorer.threshold,
        "no_arguments_rule": shortcut(scorer),
        "authentic_listings": anyio.run(local_listings, scorer, args.node, args.node_modules),
    }, indent=2))


if __name__ == "__main__":
    main()
