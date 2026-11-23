"""Collect pinned local MCP listings and evaluate a frozen L3 artifact."""

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory

import anyio
import mcp_types as types
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from pydantic import BaseModel, Field

from gateway.canonical import tool_hash
from gateway.l1_pins import L1Result
from gateway.l2_capability import L2Analyzer
from gateway.l3 import Scorer
from gateway.ladder import decide

from .mcptox_ingest import ROOT


class ListingPage(BaseModel):
    tools: list[dict]
    next_cursor: str | None = Field(default=None, alias="nextCursor")


SCHEMAS = ("missing", "invalid_or_ambiguous", "zero_parameters", "optional_only", "required")
METRICS = {
    "direct_l2": "scorable",
    "baseline_removed": "baseline_evaluated",
    "additional_l3": "baseline_served",
}
DESCRIPTION_TOPICS = {
    "files": re.compile(r"\b(?:files?|directories|directory|filesystem)\b", re.I),
    "credentials": re.compile(r"\b(?:credentials?|passwords?|api keys?|authentication|access tokens?)\b", re.I),
    "networking": re.compile(r"\b(?:https?|network|urls?|endpoints?)\b", re.I),
}


def schema_group(tool):
    schema = tool.get("inputSchema")
    if schema is None:
        return "missing"
    if not isinstance(schema, dict) or schema.get("type") != "object":
        return "invalid_or_ambiguous"
    properties, required = schema.get("properties"), schema.get("required", [])
    if (not isinstance(required, list) or any(not isinstance(key, str) for key in required)
            or any(key in schema for key in ("$ref", "patternProperties", "allOf", "anyOf", "oneOf"))):
        return "invalid_or_ambiguous"
    if properties is None and schema.get("additionalProperties") is False and not required:
        return "zero_parameters"
    if (not isinstance(properties, dict) or not set(required) <= properties.keys()
            or not all(isinstance(value, (dict, bool)) for value in properties.values())):
        return "invalid_or_ambiguous"
    if required:
        return "required"
    return "optional_only" if properties else "zero_parameters"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_inputs(manifest, artifact):
    expected = manifest["hashes"]
    for name in ("manifest.json", "classifier.joblib"):
        if sha256(artifact / name) != expected["artifact"][name]:
            raise ValueError(f"Frozen artifact changed: {name}")
    taxonomy = {path.name: sha256(path) for path in sorted((ROOT / "taxonomy").glob("*.yaml"))}
    if taxonomy != expected["taxonomy"]:
        raise ValueError("Frozen L2 taxonomy changed")


def describe_error(error):
    if isinstance(error, BaseExceptionGroup):
        return "; ".join(describe_error(cause) for cause in error.exceptions)
    return f"{type(error).__name__}: {error}" if str(error) else type(error).__name__


def sandbox_command(source, packages, node, work):
    package = packages / source["package"]
    metadata = json.loads((package / "package.json").read_text())
    if metadata["name"] != source["package"] or metadata["version"] != source["version"]:
        raise ValueError("Installed package does not match the frozen version")
    command = [
        "bwrap", "--unshare-all", "--die-with-parent", "--clearenv",
        "--ro-bind", "/usr", "/usr", "--ro-bind", "/lib", "/lib",
        "--ro-bind", "/lib64", "/lib64", "--symlink", "usr/bin", "/bin",
        "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
        "--ro-bind", str(packages), "/app/node_modules", "--ro-bind", str(node), "/node",
        "--bind", str(work), "/work", "--chdir", "/work",
        "--setenv", "HOME", "/work", "--setenv", "PATH", "/usr/bin:/bin",
    ]
    for key, value in source.get("environment", {}).items():
        command.extend(["--setenv", key, value])
    return command + ["--", "/node", f"/app/node_modules/{source['package']}/{source['entry']}", *source.get("args", [])]


async def read_listing(parameters, timeout, stderr):
    tools = []
    cursors = set()
    cursor = None
    with anyio.fail_after(timeout):
        async with stdio_client(parameters, errlog=stderr) as streams, ClientSession(*streams) as session:
            await session.initialize()
            while True:
                request = types.ListToolsRequest(params=types.PaginatedRequestParams(cursor=cursor))
                page = await session.send_request(request, ListingPage)
                tools.extend(page.tools)
                cursor = page.next_cursor
                if cursor is None:
                    return tools
                if cursor in cursors or len(cursors) == 99:
                    raise ValueError("Listing pagination did not terminate")
                cursors.add(cursor)


async def collect(manifest, packages, node, destination):
    async def collect_one(source):
        family = source["family"]
        stderr_path = destination / f"{family}.stderr"
        try:
            with TemporaryDirectory(prefix="l3-external-") as directory, stderr_path.open("w") as stderr:
                command = sandbox_command(source, packages, node, Path(directory))
                params = StdioServerParameters(command=command[0], args=command[1:])
                async with slots:
                    tools = await read_listing(params, source.get("timeout", 18), stderr)
            if not tools:
                raise ValueError("Empty tool listing")
            outcome[family] = {"status": "complete", "tools": tools}
        except Exception as error:
            outcome[family] = {"status": "excluded", "error": describe_error(error)}

    slots = anyio.Semaphore(5)
    outcome = {}
    async with anyio.create_task_group() as tasks:
        for source in manifest["sources"]:
            tasks.start_soon(collect_one, source)
    return outcome


def valid_tool(tool, group):
    if group in {"missing", "invalid_or_ambiguous"}:
        return False
    name = tool.get("name")
    description = tool.get("description")
    return isinstance(name, str) and bool(name) and (description is None or isinstance(description, str))


def score_listing(family, tools, analyzer, scorer, k):
    groups = [schema_group(tool) for tool in tools]
    valid = [valid_tool(tool, group) for tool, group in zip(tools, groups, strict=True)]
    scorable = [tool for tool, ok in zip(tools, valid, strict=True) if ok]
    flags = [analyzer(tool) for tool in scorable]
    scores = iter(scorer.score_listing(scorable))
    findings = iter(flags)
    names = [tool["name"] for tool in scorable]
    replayable = all(valid) and len(names) == len(set(names))
    removed = {}
    if replayable:
        l1 = {name: L1Result("new", None, "") for name in names}
        l2 = dict(zip(names, flags, strict=True))
        removed = decide(family, names, l1, l2, k).removed

    rows = []
    for position, (tool, group, ok) in enumerate(zip(tools, groups, valid, strict=True)):
        description = tool.get("description")
        description = description if isinstance(description, str) else ""
        row = {"family": family, "position": position, "tool": tool.get("name"), "schema_group": group,
               "description_chars": len(description),
               "description_topics": [topic for topic, pattern in DESCRIPTION_TOPICS.items()
                                      if pattern.search(description)],
               "scorable": ok, "baseline_evaluated": replayable,
               "baseline_served": replayable and tool["name"] not in removed,
               "baseline_removed": replayable and tool["name"] in removed}
        if ok:
            l3 = next(scores)
            reason = removed.get(tool["name"])
            row.update(fingerprint=tool_hash(tool), l2=[flag.as_dict() for flag in next(findings)],
                       l3=l3, decision_reason=reason)
            row["direct_l2"] = bool(row["l2"])
            row["additional_l3"] = row["baseline_served"] and l3["verdict"] == "flagged"
        rows.append(row)
    return rows


def summarize(rows):
    tools = defaultdict(list)
    for row in rows:
        key = row.get("fingerprint") or (row["family"], row["position"])
        tools[key].append(row)
    summary = {"unique_tools": len(tools), "families": len({row["family"] for row in rows})}
    for metric, denominator in METRICS.items():
        eligible = [row for row in rows if row.get(denominator)]
        summary[metric] = {
            "tools": sum(any(row.get(metric) for row in group) for group in tools.values()),
            "tool_denominator": sum(any(row.get(denominator) for row in group) for group in tools.values()),
            "families": len({row["family"] for row in eligible if row.get(metric)}),
            "family_denominator": len({row["family"] for row in eligible}),
        }
    return summary


def evaluate(frozen, artifact):
    manifest = frozen["manifest"]
    verify_inputs(manifest, artifact)
    scorer = Scorer(artifact)
    analyzer = L2Analyzer.from_dir(ROOT / "taxonomy")
    by_family = {}
    for source in manifest["sources"]:
        family = source["family"]
        entry = frozen["listings"][family]
        if entry["status"] == "complete":
            by_family[family] = score_listing(family, entry["tools"], analyzer, scorer, manifest["k"])
    cohorts = {}
    for cohort in sorted({source["cohort"] for source in manifest["sources"]}):
        rows = [row for source in manifest["sources"] if source["cohort"] == cohort
                for row in by_family.get(source["family"], [])]
        cohorts[cohort] = {
            "overall": summarize(rows),
            "by_schema": {key: summarize([row for row in rows if row["schema_group"] == key]) for key in SCHEMAS},
            "long_descriptions": summarize([row for row in rows if row["description_chars"] >= 300]),
            "by_description_topic": {topic: summarize([row for row in rows if topic in row["description_topics"]])
                                     for topic in DESCRIPTION_TOPICS},
            "by_family": {family: summarize(family_rows) for family, family_rows in by_family.items()
                          if any(row["family"] == family for row in rows)},
        }
    return {"threshold": scorer.threshold, "k": manifest["k"], "cohorts": cohorts, "per_family": by_family,
            "excluded_sources": {family: entry["error"] for family, entry in frozen["listings"].items()
                                 if entry["status"] == "excluded"}}


def write_json(path, value):
    with path.open("x") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("collect", "evaluate"))
    parser.add_argument("--manifest", type=Path, default=ROOT / "eval/sources/l3_external.json")
    parser.add_argument("--artifact", type=Path, default=ROOT / "var/l3")
    parser.add_argument("--packages", type=Path, default=ROOT / "var/l3-external-packages/node_modules")
    parser.add_argument("--node", type=Path, default=Path("/usr/bin/node"))
    parser.add_argument("--output", type=Path, default=ROOT / "var/l3-external")
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    capture = args.output / "listings.json"
    if args.phase == "collect":
        if capture.exists():
            parser.error("choose a new output directory for a new collection")
        manifest = json.loads(args.manifest.read_text())
        verify_inputs(manifest, args.artifact)
        packages, node = args.packages.resolve(), args.node.resolve()
        if sha256(packages.parent / "package-lock.json") != manifest["hashes"]["npm_lock"]:
            parser.error("package lock does not match the frozen manifest")
        if sha256(node) != manifest["hashes"]["node"]:
            parser.error("Node executable does not match the frozen manifest")
        listings = anyio.run(collect, manifest, packages, node, args.output)
        write_json(capture, {"manifest": manifest, "listings": listings})
        for family, item in sorted(listings.items()):
            print(f"{family}: {len(item['tools'])} tools" if item["status"] == "complete" else f"{family}: excluded")
    else:
        report = evaluate(json.loads(capture.read_text()), args.artifact)
        report["listing_capture_sha256"] = sha256(capture)
        write_json(args.output / "results.json", report)


if __name__ == "__main__":
    main()
