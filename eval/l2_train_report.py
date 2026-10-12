"""L2 on the MCPTox TRAIN split only (pattern tuning happens here; held-out is never read).

Prints per-risk-category recall (poisoned tool flagged), micro/macro average, and the FP count on
train authentic tools. Always with n.
"""

import collections
import sys

from gateway.config import ROOT
from gateway.l2_capability import L2Analyzer

from .mcptox_ingest import load
from .split import load_split


def main(verbose: bool = False) -> None:
    split = load_split()
    data = load()["servers"]
    l2 = L2Analyzer.from_dir(ROOT / "taxonomy")
    servers = split["train_servers"]
    hit, tot = collections.Counter(), collections.Counter()
    misses = []
    for s in servers:
        for c in data[s]["cases"]:
            tot[c["risk"]] += 1
            if l2(c["poisoned_tool"]):
                hit[c["risk"]] += 1
            else:
                misses.append(c)
    print(f"L2 recall on MCPTox TRAIN split (preliminary; {len(servers)} servers, n={sum(tot.values())} cases)")
    print(f"{'risk category':28s} {'flagged':>8s} {'n':>5s} {'recall':>7s}")
    for r in sorted(tot):
        print(f"{r:28s} {hit[r]:8d} {tot[r]:5d} {hit[r] / tot[r]:7.1%}")
    micro = sum(hit.values()) / sum(tot.values())
    macro = sum(hit[r] / tot[r] for r in tot) / len(tot)
    print(f"{'micro-average':28s} {sum(hit.values()):8d} {sum(tot.values()):5d} {micro:7.1%}")
    print(f"{'macro-average (over ' + str(len(tot)) + ' cats)':28s} {'':8s} {'':5s} {macro:7.1%}")

    fps = [(s, t) for s in servers for t in data[s]["authentic_tools"] if l2(t)]
    n_auth = sum(len(data[s]["authentic_tools"]) for s in servers)
    print(f"\nFalse positives on TRAIN authentic tools: {len(fps)} / n={n_auth}")
    for s, t in fps:
        for f in l2(t):
            print(f"  FP {s}/{t['name']}: {f}")
    if verbose:
        print("\nSample misses:")
        for c in misses[:: max(1, len(misses) // 25)]:
            print(f"  MISS [{c['risk']}] {c['server']}/{c['poisoned_tool']['name']}: {c['poisoned_tool']['description'][:160]!r}")


if __name__ == "__main__":
    main("-v" in sys.argv)
