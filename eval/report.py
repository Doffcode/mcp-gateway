"""Demo 4 numbers -> results/results.csv + results/results.md. Every number carries n; rates carry a 95% CI.

Deterministic parts (no LLM): FPR on all 353 authentic tools, hard-negative stress test, L2 detection on the
held-out split, p95 latency of L1+L2+ladder. LLM part: ASR without vs with the gateway from eval.run_mcptox output.
CIs: case-level bootstrap, 1,000 resamples, fixed seed (single run, so they cover sampling of cases only).

  uv run python -m eval.report var/eval/mcptox_heldout_n300_think-on.jsonl
"""

import collections
import csv
import json
import random
import re
import statistics
import sys
import tempfile
import time
from pathlib import Path

from gateway.config import ROOT
from gateway.l1_pins import PinStore
from gateway.l2_capability import L2Analyzer
from gateway.ladder import decide

from .judge import agreement
from .mcptox_ingest import load
from .split import SEED, load_split

OUT = ROOT / "results"
B = 1000
K = 2


def boot_ci(values: list[float], stat=statistics.fmean, seed: int = SEED) -> tuple[float, float]:
    if not values:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    n = len(values)
    s = sorted(stat([values[rng.randrange(n)] for _ in range(n)]) for _ in range(B))
    return s[int(0.025 * B)], s[int(0.975 * B) - 1]


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


class Report:
    def __init__(self, model: str):
        self.rows, self.md, self.model = [], [], model

    def add(self, metric, subset, condition, k, n, value, ci=(None, None), note=""):
        self.rows.append({"metric": metric, "subset": subset, "condition": condition, "k": k, "n": n,
                          "value": round(value, 4), "ci95_lo": None if ci[0] is None else round(ci[0], 4),
                          "ci95_hi": None if ci[1] is None else round(ci[1], 4), "model": self.model, "note": note})


def run_ladder(server, tools, l2):
    with tempfile.TemporaryDirectory() as d:
        pins = PinStore(Path(d) / "p.json")
        l1 = {t["name"]: pins.check(server, t) for t in tools}
    return decide(server, [t["name"] for t in tools], l1, {t["name"]: l2(t) for t in tools}, K)


def static_part(rep: Report, data, split, l2):
    md = rep.md
    # --- FPR on all 353 authentic tools (servers as served, no poisoned tool) -----------------------------
    per_tool, quarantined, fp_list = [], [], []
    for s, d in sorted(data.items()):
        dec = run_ladder(s, d["authentic_tools"], l2)
        if dec.quarantined:
            quarantined.append(s)
        for t in d["authentic_tools"]:
            removed = t["name"] in dec.removed
            per_tool.append((s, t, removed))
            if removed:
                fp_list.append((s, t["name"], dec.removed[t["name"]]))
    md.append("## False positives on authentic tools (deterministic, no LLM)\n")
    md.append("| subset | removed | n tools | FPR | 95% CI |\n|---|---|---|---|---|")
    for subset, servers in (("all 353", set(data)), ("train servers (L2 tuned here)", set(split["train_servers"])),
                            ("held-out servers", set(split["heldout_servers"]))):
        v = [float(r) for s, t, r in per_tool if s in servers]
        ci = boot_ci(v)
        rep.add("FPR_tool_level", subset, "gateway L1+L2", K, len(v), statistics.fmean(v), ci)
        md.append(f"| {subset} | {int(sum(v))} | {len(v)} | {pct(statistics.fmean(v))} | {pct(ci[0])}–{pct(ci[1])} |")
    rep.add("servers_quarantined", "all 45", "gateway L1+L2", K, len(data), len(quarantined) / len(data),
            note=";".join(quarantined))
    md.append(f"\nServers quarantined at K={K} with no attack present: **{len(quarantined)} / n={len(data)}** "
              f"({', '.join(quarantined) or 'none'}). Each quarantine removes every tool of that server.\n")
    md.append("Removed authentic tools:\n")
    for s, n, why in fp_list:
        md.append(f"- `{s}/{n}`: {why}")

    # --- hard negatives -----------------------------------------------------------------------------------
    trig = {w.strip() for w in (ROOT / "data" / "hard_negative_triggers.txt").read_text().splitlines()
            if w.strip() and not w.startswith("#")}
    hn = [(s, t, r) for s, t, r in per_tool
          if set(re.findall(r"[a-z0-9]+", (t["name"] + " " + t["description"]).lower())) & trig]
    fp = sum(r for _, _, r in hn)
    md.append("\n## Hard-negative stress test (separate from the headline FPR)\n")
    md.append(f"Authentic tools whose name/description contains a MITRE ATT&CK v19.2 trigger word "
              f"(list frozen in commit facb89f before L2 existed): **n = {len(hn)}**. Removed by the gateway: "
              f"**{fp}** ({pct(fp / len(hn))}).")
    if fp == 0:
        md.append(f" Zero removals; rule-of-three 95% upper bound = 3/n = {pct(3 / len(hn))}.")
    rep.add("FPR_hard_negatives", "trigger-word subset of 353", "gateway L1+L2", K, len(hn), fp / len(hn),
            (0.0, 3 / len(hn)) if fp == 0 else boot_ci([float(r) for *_, r in hn]),
            note="rule-of-three upper bound" if fp == 0 else "")

    # --- L2 detection of the poisoned tool on held-out (no LLM) --------------------------------------------
    md.append("\n## Detection: poisoned tool removed by the gateway, held-out split (deterministic, no LLM)\n")
    md.append("Each case = the server's authentic tools + that case's poisoned tool, one tools/list. "
              "'Removed' includes removal via server quarantine.\n")
    md.append("| risk category | removed | n | rate | 95% CI |\n|---|---|---|---|---|")
    by = collections.defaultdict(list)
    for s in split["heldout_servers"]:
        for c in data[s]["cases"]:
            dec = run_ladder(s, data[s]["authentic_tools"] + [c["poisoned_tool"]], l2)
            by[c["risk"]].append(float(c["poisoned_tool"]["name"] in dec.removed))
    allv = [x for v in by.values() for x in v]
    for r in sorted(by):
        ci = boot_ci(by[r])
        md.append(f"| {r} | {int(sum(by[r]))} | {len(by[r])} | {pct(statistics.fmean(by[r]))} | {pct(ci[0])}–{pct(ci[1])} |")
        rep.add("detection_rate", r, "gateway L1+L2", K, len(by[r]), statistics.fmean(by[r]), ci)
    ci = boot_ci(allv)
    macro = statistics.fmean(statistics.fmean(v) for v in by.values())
    md.append(f"| **micro** | {int(sum(allv))} | {len(allv)} | {pct(statistics.fmean(allv))} | {pct(ci[0])}–{pct(ci[1])} |")
    md.append(f"| **macro** ({len(by)} categories) | | | {pct(macro)} | |")
    md.append("\n'Other' (n=4) has no held-out cases (n=0), so it is not shown.")
    rep.add("detection_rate", "micro held-out", "gateway L1+L2", K, len(allv), statistics.fmean(allv), ci)
    rep.add("detection_rate", "macro held-out", "gateway L1+L2", K, len(by), macro, note="mean over categories")

    # --- latency ------------------------------------------------------------------------------------------
    reps = 50
    miss, hit = [], []
    with tempfile.TemporaryDirectory() as d:
        for i in range(reps):
            for s, sd in sorted(data.items()):
                tools = sd["authentic_tools"]
                pins = PinStore(Path(d) / f"p{i}_{s}.json")
                for bucket in (miss, hit):  # first sight (pin written to disk), then pinned
                    t0 = time.perf_counter()
                    l1 = {t["name"]: pins.check(s, t) for t in tools}
                    decide(s, [t["name"] for t in tools], l1, {t["name"]: l2(t) for t in tools}, K)
                    bucket.append((time.perf_counter() - t0) * 1000)
    md.append("\n## Latency of L1+L2+ladder per tools/list (gateway overhead only, excludes the upstream round trip)\n")
    md.append("| case | n tools/list calls | p50 ms | p95 ms |\n|---|---|---|---|")
    for name, v in (("first sight (pin written to disk)", miss), ("already pinned", hit)):
        q = statistics.quantiles(v, n=100)
        md.append(f"| {name} | {len(v)} | {q[49]:.2f} | {q[94]:.2f} |")
        rep.add("latency_p95_ms", name, "gateway L1+L2", K, len(v), q[94], note=f"p50={q[49]:.3f}ms; 45 servers x {reps} reps")
    sizes = [len(sd["authentic_tools"]) for sd in data.values()]
    md.append(f"\nServers have {min(sizes)}–{max(sizes)} tools (median {statistics.median(sizes)}). "
              "Measured on the lab PC (single process, Python 3.12).")


def asr_part(rep: Report, path: Path):
    md = rep.md
    rs = [json.loads(x) for x in path.read_text().splitlines()]
    by = collections.defaultdict(dict)
    for r in rs:
        by[r["id"]][r["condition"]] = r
    cases = [v for v in by.values() if "no_defense" in v and "gateway" in v]
    n = len(cases)
    model = cases[0]["no_defense"]["model"]
    think = cases[0]["no_defense"]["think"]
    nd = [float(c["no_defense"]["success"]) for c in cases]
    gw = [float(c["gateway"]["success"]) for c in cases]
    delta = [a - b for a, b in zip(nd, gw)]
    ref = [c for c in cases if c["no_defense"]["mcptox_label_qwen3_8b"] not in (None,)]
    refv = [float(c["no_defense"]["mcptox_label_qwen3_8b"] == "Success") for c in ref]
    md.insert(0, "")
    head = [f"## Attack success rate (ASR), MCPTox held-out, stratified sample\n",
            f"Model **{model}** (think={'on' if think else 'off'}), Ollama, temperature 0, seed {SEED}, single run. "
            f"**n = {n} cases** (proportional stratified by risk category, seed {SEED}). "
            "Success judged by the deterministic `eval/judge.py` (see judge agreement below).\n",
            "| condition | successes | n | ASR | 95% CI |", "|---|---|---|---|---|"]
    for name, v in (("no defense", nd), ("gateway (L1+L2)", gw)):
        ci = boot_ci(v)
        head.append(f"| {name} | {int(sum(v))} | {n} | {pct(statistics.fmean(v))} | {pct(ci[0])}–{pct(ci[1])} |")
        rep.add("ASR_micro", f"held-out sample n={n}", name, K, n, statistics.fmean(v), ci)
    ci = boot_ci(delta)
    head.append(f"| **ΔASR (no defense − gateway)** | | {n} | **{100 * statistics.fmean(delta):.1f} pp** | "
                f"{100 * ci[0]:.1f}–{100 * ci[1]:.1f} pp |")
    rep.add("delta_ASR_pp", f"held-out sample n={n}", "no defense - gateway", K, n, 100 * statistics.fmean(delta),
            (100 * ci[0], 100 * ci[1]), note="paired case-level bootstrap")
    refci = boot_ci(refv)
    head.append(f"\nReference: MCPTox's own label for Qwen3-8b-{'Think' if think else 'No-Think'} on the same cases: "
                f"ASR {pct(statistics.fmean(refv))} (n={len(refv)}, CI {pct(refci[0])}–{pct(refci[1])}). "
                "Different runtime/quantisation and a different judge, so only a sanity check.")
    rep.add("ASR_reference_MCPTox_label", f"same cases n={len(refv)}", "no defense (MCPTox paper run)", "", len(refv),
            statistics.fmean(refv), refci)

    # per category + macro
    cat = collections.defaultdict(lambda: ([], []))
    for c in cases:
        cat[c["no_defense"]["risk"]][0].append(float(c["no_defense"]["success"]))
        cat[c["no_defense"]["risk"]][1].append(float(c["gateway"]["success"]))
    head.append("\n| risk category | n | ASR no defense | ASR gateway |\n|---|---|---|---|")
    for r in sorted(cat):
        a, b = cat[r]
        head.append(f"| {r} | {len(a)} | {int(sum(a))} ({pct(statistics.fmean(a))}) | {int(sum(b))} ({pct(statistics.fmean(b))}) |")
        rep.add("ASR_by_category", r, "no defense", K, len(a), statistics.fmean(a))
        rep.add("ASR_by_category", r, "gateway (L1+L2)", K, len(b), statistics.fmean(b))
    ma = statistics.fmean(statistics.fmean(a) for a, _ in cat.values())
    mb = statistics.fmean(statistics.fmean(b) for _, b in cat.values())
    head.append(f"| **macro** ({len(cat)} categories) | {n} | {pct(ma)} | {pct(mb)} |")
    rep.add("ASR_macro", f"held-out sample n={n}", "no defense", K, len(cat), ma, note="mean over categories")
    rep.add("ASR_macro", f"held-out sample n={n}", "gateway (L1+L2)", K, len(cat), mb, note="mean over categories")

    # what the gateway did in these cases
    removed = sum(c["gateway"]["gateway"]["poison_removed"] for c in cases)
    quar = sum(c["gateway"]["gateway"]["quarantined"] for c in cases)
    other = sum(bool(set(c["gateway"]["gateway"]["removed"]) - {c["gateway"]["gateway"].get("poison", "")})
                and not c["gateway"]["gateway"]["poison_removed"] for c in cases)
    residual = [c for c in cases if c["gateway"]["success"]]
    trunc = sum(c[k]["done_reason"] == "length" for c in cases for k in ("no_defense", "gateway"))
    head.append(f"\nIn these n={n} cases the gateway removed the poisoned tool in **{removed}** "
                f"({quar} via server quarantine). In {other} cases it missed the poisoned tool but removed an "
                "authentic tool (false positive), which can also change the model's behaviour. "
                f"Residual successes with the gateway on: **{len(residual)}** (L2 misses: wording outside the "
                "taxonomy's vocabulary, mostly parameter tampering of legitimate tools). "
                f"Responses cut at the token limit: {trunc}/{2 * n}.")
    for c in residual[:15]:
        head.append(f"- miss `{c['gateway']['id']}` [{c['gateway']['risk']}]")
    md[0:0] = head
    return model, think, n


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    data = load()["servers"]
    split = load_split()
    l2 = L2Analyzer.from_dir(ROOT / "taxonomy")
    rep = Report("qwen3:8b")
    static_part(rep, data, split, l2)
    title = ["# Results: PRELIMINARY (Phase-2 review)\n",
             "Every number below is preliminary, single-run, with its n. L3 (semantic classifier) and L4 are not "
             "built; 'gateway' = L1 provenance pinning + L2 capability consistency + decision ladder (K=2). "
             "On MCPTox every tool is seen for the first time, so L1 only pins (TOFU) and contributes nothing to "
             "these numbers; L1 is shown by Demo 1 (rug-pull). L2 is deterministic and auditable; wording outside "
             "the taxonomy's vocabulary can evade it.\n"]
    if path:
        model, think, n = asr_part(rep, path)
        ag = agreement("heldout", models=(f"Qwen3-8b-{'Think' if think else 'No-Think'}",))
        a = next(iter(ag.values()))
        rep.md.append(f"\n## Judge validity\n\nOur deterministic judge vs MCPTox's own labels on MCPTox's stored "
                      f"Qwen3-8b-{'Think' if think else 'No-Think'} responses, held-out split (judge rules written on "
                      f"train only): 4-way agreement {a['agree']}/{a['n']} = {pct(a['agree'] / a['n'])}. On 'Success': "
                      f"{a['tp']} agree, {a['fp']} judged Success but labelled otherwise, {a['fn']} labelled Success "
                      f"but missed by our judge. Our judge therefore tends to **under-count** ASR in this mode.")
        rep.add("judge_agreement", "held-out stored MCPTox responses", f"Qwen3-8b think={think}", "", a["n"],
                a["agree"] / a["n"])
    OUT.mkdir(exist_ok=True)
    (OUT / "results.md").write_text("\n".join(title + rep.md) + "\n")
    with (OUT / "results.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rep.rows[0]))
        w.writeheader()
        w.writerows(rep.rows)
    print((OUT / "results.md").read_text())


if __name__ == "__main__":
    main()
