"""Build labeled metadata examples and compute first-sight L1+L2 decisions."""

from dataclasses import dataclass

from gateway.l1_pins import L1Result
from gateway.ladder import decide
from gateway.l3 import metadata_text
from gateway.l2_capability import L2Analyzer

from .mcptox_ingest import ROOT


@dataclass
class Example:
    server: str
    label: int
    risk: str
    l2_flag: bool
    baseline_removed: bool
    text: str
    context_text: str


def examples(dataset, servers, k):
    l2 = L2Analyzer.from_dir(ROOT / "taxonomy")
    rows = []
    for server in servers:
        entry = dataset[server]
        authentic = entry["authentic_tools"]
        clean_flags = {tool["name"]: l2(tool) for tool in authentic}
        known = {name: L1Result("new", None, "") for name in clean_flags}
        clean_decision = decide(server, list(clean_flags), known, clean_flags, k)
        for tool in authentic:
            name = tool["name"]
            rows.append(Example(server, 0, "authentic", bool(clean_flags[name]),
                                name in clean_decision.removed, metadata_text(tool),
                                metadata_text(tool, authentic, use_context=True)))
        for case in entry["cases"]:
            tool = case["poisoned_tool"]
            name = tool["name"]
            flags = l2(tool)
            case_flags = {**clean_flags, name: flags}
            decision = decide(server, list(case_flags), {**known, name: L1Result("new", None, "")}, case_flags, k)
            listing = [sibling for sibling in authentic if sibling["name"] != name] + [tool]
            rows.append(Example(server, 1, case["risk"], bool(flags), name in decision.removed,
                                metadata_text(tool), metadata_text(tool, listing, use_context=True)))
    return rows
