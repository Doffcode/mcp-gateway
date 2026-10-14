"""MCPTox in the Gateway Lab: browse real cases, run the real proxy and the real model on them, sweep the benchmark live.

Everything reuses the evaluation code (eval/run_mcptox.py, eval/judge.py, eval/report.py), so what the panel sees is
computed by the same functions that produced results/results.md.
"""

import collections
import datetime
import json
import statistics
import time
from functools import lru_cache
from pathlib import Path

from eval.judge import judge
from eval.mcptox_ingest import RAW, load
from eval.report import boot_ci, run_ladder
from eval.run_mcptox import Model, cut_blocks, gateway_view
from eval.split import load_split
from gateway.l2_capability import L2Analyzer

from .lab import LabSession
from .scenarios import ROOT, TAXONOMY, tool_card

RUN_FILE = ROOT / "var" / "eval" / "mcptox_heldout_n300_think-on.jsonl"
K = 2


@lru_cache(maxsize=1)
def data() -> dict:
    return load()["servers"]


@lru_cache(maxsize=1)
def raw() -> dict:
    return json.loads(RAW.read_text())["servers"]


@lru_cache(maxsize=1)
def split() -> dict:
    return load_split()


@lru_cache(maxsize=1)
def l2() -> L2Analyzer:
    return L2Analyzer.from_dir(TAXONOMY)


def _case(cid: str) -> dict:
    s = cid.split("#")[0]
    return next(c for c in data()[s]["cases"] if c["id"] == cid)


def servers_index() -> list[dict]:
    held = set(split()["heldout_servers"])
    return [{"server": s, "split": "held-out" if s in held else "train", "n_tools": len(d["authentic_tools"]),
             "cases": [{"id": c["id"], "risk": c["risk"], "paradigm": c["paradigm"]} for c in d["cases"]]}
            for s, d in sorted(data().items())]


def stored_results(cid: str) -> list[dict]:
    """The n=300 run file's records for this case, with their line numbers (provenance)."""
    if not RUN_FILE.exists():
        return []
    out = []
    for i, line in enumerate(RUN_FILE.read_text().splitlines(), 1):
        r = json.loads(line)
        if r["id"] == cid:
            out.append({"line": i, "file": str(RUN_FILE.relative_to(ROOT)), "condition": r["condition"],
                        "label": r["label"], "response": r["response"], "seconds": r["seconds"],
                        "reused_no_defense": r.get("reused_no_defense", False)})
    return out


def case_info(cid: str) -> dict:
    c = _case(cid)
    s = c["server"]
    idx = int(cid.split("#")[1])
    labels = raw()[s]["malicious_instance"][idx]["datas"][0]["label"]
    return {"id": cid, "server": s, "risk": c["risk"], "paradigm": c["paradigm"], "query": c["query"],
            "split": "held-out" if s in split()["heldout_servers"] else "train",
            "poisoned": tool_card(c["poisoned_tool"]), "n_authentic": len(data()[s]["authentic_tools"]),
            "mcptox_labels": labels, "stored": stored_results(cid)}


async def case_gateway(cid: str) -> dict:
    """Serve the case from the MCPTox replay server through the REAL proxy (stdio, tapped) and report what happened.
    Also returns the in-process gateway_view() decision used by the benchmark, to show they agree."""
    c = _case(cid)
    lab = LabSession()
    try:
        r = await lab.connect([{"kind": "mcptox", "opts": {"server": c["server"], "case": cid}}], gateway=True)
    finally:
        await lab.disconnect()
    srv = r["servers"][c["server"]]
    gv = gateway_view(c["server"], data()[c["server"]]["authentic_tools"], c["poisoned_tool"], K, l2())
    return {**srv, "poisoned_name": c["poisoned_tool"]["name"], "procs": r["procs"],
            "frames": [x for x in lab._read(lab.wire) if "proc" not in x],
            "gateway_view": gv, "agree": sorted(srv["removed"]) == gv["removed"]}


def case_run(cid: str, cond: str, think: bool) -> dict:
    """One live model call in the MCPTox protocol (its system prompt + query), judged deterministically."""
    c = _case(cid)
    s = c["server"]
    auth = data()[s]["authentic_tools"]
    dd = raw()[s]["malicious_instance"][int(cid.split("#")[1])]["datas"][0]
    gv = gateway_view(s, auth, c["poisoned_tool"], K, l2())
    system = c["system_prompt"] if cond == "no_defense" else cut_blocks(c["system_prompt"], dd["poisoned_tool"],
                                                                         set(gv["removed"]), c["poisoned_tool"]["name"])
    m = Model(think, 4096)
    res = m(system, c["query"])
    label = judge(res["response"], c["poisoned_tool"], c["query"], [] if gv["quarantined"] and cond == "gateway" else auth)
    rec = {"id": cid, "server": s, "risk": c["risk"], "condition": cond, "model": m.name, "think": think,
           "prompt_chars": len(system), "prompt_chars_original": len(c["system_prompt"]), "cut_tools": gv["removed"] if cond == "gateway" else [],
           "response": res["response"], "seconds": round(res["seconds"], 2), "done_reason": res["done_reason"],
           "label": label, "success": label == "Success",
           "mcptox_label": dd["label"].get("Qwen3-8b-Think" if think else "Qwen3-8b-No-Think"),
           "when": datetime.datetime.now().isoformat(timespec="seconds")}
    out = ROOT / "var" / "eval" / f"live_{datetime.date.today()}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return {**rec, "saved_to": str(out.relative_to(ROOT))}


def model_status() -> dict:
    from eval.run_mcptox import local_cfg

    import ollama

    cfg = local_cfg()
    try:
        names = [m.model for m in ollama.Client(host=cfg["ollama_host"], timeout=3).list().models]
        return {"ok": cfg["model"] in names, "model": cfg["model"], "host": cfg["ollama_host"], "available": names}
    except Exception as e:
        return {"ok": False, "model": cfg["model"], "host": cfg["ollama_host"], "error": type(e).__name__}


def sweep():
    """Generator of events: the gateway on every held-out case, then FPR on all 353 authentic tools, then stats."""
    by = collections.defaultdict(list)
    times = []
    held = [c for s in split()["heldout_servers"] for c in data()[s]["cases"]]
    yield {"kind": "start", "n_cases": len(held), "n_tools": sum(len(d["authentic_tools"]) for d in data().values())}
    for i, c in enumerate(held, 1):
        t0 = time.perf_counter()
        gv = gateway_view(c["server"], data()[c["server"]]["authentic_tools"], c["poisoned_tool"], K, l2())
        times.append((time.perf_counter() - t0) * 1000)
        by[c["risk"]].append(float(gv["poison_removed"]))
        yield {"kind": "case", "i": i, "id": c["id"], "risk": c["risk"], "removed": gv["poison_removed"],
               "quarantined": gv["quarantined"], "ms": round(times[-1], 2)}
    allv = [x for v in by.values() for x in v]
    det = {"micro": statistics.fmean(allv), "ci": boot_ci(allv), "n": len(allv), "hits": int(sum(allv)),
           "macro": statistics.fmean(statistics.fmean(v) for v in by.values()),
           "by_risk": {r: {"hits": int(sum(v)), "n": len(v)} for r, v in sorted(by.items())}}
    fp = []
    quarantined = []
    for s, d in sorted(data().items()):
        dec = run_ladder(s, d["authentic_tools"], l2())
        if dec.quarantined:
            quarantined.append(s)
        for t in d["authentic_tools"]:
            fp.append(float(t["name"] in dec.removed))
            yield {"kind": "tool", "server": s, "tool": t["name"], "removed": t["name"] in dec.removed,
                   "reason": dec.removed.get(t["name"], "")}
    q = statistics.quantiles(times, n=100)
    yield {"kind": "done", "detection": det,
           "fpr": {"value": statistics.fmean(fp), "ci": boot_ci(fp), "removed": int(sum(fp)), "n": len(fp)},
           "quarantined": quarantined, "n_servers": len(data()),
           "latency": {"p50": q[49], "p95": q[94], "n": len(times), "note": "in-process L1+L2+ladder per tools/list, measured now"}}


def asr_from_file(path: Path = RUN_FILE) -> dict:
    """ASR with and without the gateway, recomputed now from the run file (same statistics as eval/report.py)."""
    if not path.exists():
        return {"ok": False, "file": str(path.relative_to(ROOT))}
    by = collections.defaultdict(dict)
    for r in map(json.loads, path.read_text().splitlines()):
        by[r["id"]][r["condition"]] = r
    cases = [v for v in by.values() if "no_defense" in v and "gateway" in v]
    nd = [float(c["no_defense"]["success"]) for c in cases]
    gw = [float(c["gateway"]["success"]) for c in cases]
    d = [a - b for a, b in zip(nd, gw)]
    first = cases[0]["no_defense"]
    mtime = datetime.datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="minutes")
    return {"ok": True, "file": str(path.relative_to(ROOT)), "modified": mtime, "n": len(cases),
            "model": first["model"], "think": first["think"],
            "no_defense": {"value": statistics.fmean(nd), "ci": boot_ci(nd), "hits": int(sum(nd))},
            "gateway": {"value": statistics.fmean(gw), "ci": boot_ci(gw), "hits": int(sum(gw))},
            "delta_pp": {"value": 100 * statistics.fmean(d), "ci": [100 * x for x in boot_ci(d)]}}
