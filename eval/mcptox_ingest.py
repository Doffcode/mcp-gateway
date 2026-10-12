"""Load MCPTox (as-is) from data/raw/response_all.json into plain dicts.

MCPTox ships tool metadata as prompt TEXT, not JSON schema:
    Tool: <name>\nDescription: <text>\nArguments:\n- <param>: <desc> (required)\n
We parse that into {name, description, inputSchema}. Parameter types are not available in the source,
so L2 can only use parameter names and parameter descriptions for MCPTox (documented limitation).
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "response_all.json"

_BLOCK_SPLIT = re.compile(r"(?m)^Tool:[ \t]*")
_ARG_RE = re.compile(r"^- (?P<p>[^:\n]+):[ \t]*(?P<d>.*)$")
_REQ = " (required)"


def _unescape(text: str) -> str:
    # Some MCPTox entries store newlines as the two characters backslash-n.
    return text.replace("\\n", "\n") if "\\n" in text else text


def parse_tools(text: str) -> list[dict]:
    """Parse `Tool:/Description:/Arguments:` blocks. Argument descriptions may span several lines;
    the argument list ends at the first blank line (MCPTox appends prompt instructions after it)."""
    tools = []
    for block in _BLOCK_SPLIT.split(_unescape(text))[1:]:
        name, _, rest = block.partition("\n")
        desc_part, sep, args_part = rest.partition("\nArguments:\n")
        if not sep:
            desc_part, args_part = rest, ""
        desc = re.sub(r"^Description:[ \t]*", "", desc_part.strip("\n")).strip()
        props, required, last = {}, [], None
        for line in args_part.split("\n\n")[0].splitlines():
            a = _ARG_RE.match(line)
            if a and a["p"].strip().lower() != "no arguments":
                last = a["p"].strip()
                d = a["d"].rstrip()
                if d.endswith(_REQ):
                    d = d[: -len(_REQ)]
                    required.append(last)
                props[last] = {} if d.strip() in ("", "No description") else {"description": d.strip()}
            elif a is None and last is not None and line.strip():
                cur = props[last].get("description", "")
                props[last]["description"] = (cur + " " + line.strip()).strip()
        schema = {"type": "object", "properties": props}
        if required:
            schema["required"] = required
        tools.append({"name": name.strip(), "description": desc, "inputSchema": schema})
    return tools


def load(path: Path = RAW) -> dict:
    """Returns {"servers": {name: {"authentic_tools": [...], "cases": [...]}}} with valid cases only."""
    raw = json.loads(Path(path).read_text())
    out = {}
    for sname, s in raw["servers"].items():
        # The 353 authentic tools are the ones in `tool_names` (paper's count). Apify's prompt lists 9 more
        # tools than its `tool_names`; they are kept out so n matches the paper.
        listed = set(s["tool_names"])
        authentic = [t for t in parse_tools(s["clean_system_promot"]) if t["name"] in listed]
        cases = []
        for i, inst in enumerate(s["malicious_instance"]):
            if inst.get("wrong_data"):
                continue
            poisoned = parse_tools(inst["poisoned_tool"].strip() + "\n")
            assert len(poisoned) == 1, (sname, i)
            cases.append({
                "id": f"{sname}#{i}",
                "server": sname,
                "query": inst["datas"][0]["query"],
                "system_prompt": inst["datas"][0]["system"],
                "poisoned_tool": poisoned[0],
                "paradigm": inst["metadata"]["paradigm"],
                "risk": inst["metadata"]["security risk"],
            })
        out[sname] = {"authentic_tools": authentic, "tool_names": s["tool_names"], "cases": cases}
    return {"servers": out}


if __name__ == "__main__":
    d = load()
    n_auth = sum(len(s["authentic_tools"]) for s in d["servers"].values())
    n_names = sum(len(s["tool_names"]) for s in d["servers"].values())
    n_cases = sum(len(s["cases"]) for s in d["servers"].values())
    mism = [k for k, s in d["servers"].items() if len(s["authentic_tools"]) != len(s["tool_names"])]
    print(f"servers={len(d['servers'])} authentic_tools parsed={n_auth} (listed {n_names}) valid cases={n_cases}")
    print("servers where parsed != listed:", mism)
