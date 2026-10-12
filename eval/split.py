"""Grouped-by-server train/held-out split of MCPTox (never random per case). Fixed seed, saved to disk.

Servers are shuffled with SEED and added to train until train holds >= TRAIN_FRAC of valid cases;
the rest is held out. The held-out split must not be used for L2 pattern tuning (or L3 training).
"""

import collections
import json
import random
from pathlib import Path

from .mcptox_ingest import ROOT, load

SEED = 20261012
TRAIN_FRAC = 0.6
OUT = ROOT / "data" / "split.json"


def make_split() -> dict:
    d = load()["servers"]
    names = sorted(d)
    random.Random(SEED).shuffle(names)
    total = sum(len(d[n]["cases"]) for n in names)
    train, held, acc = [], [], 0
    for n in names:
        if acc < TRAIN_FRAC * total:
            train.append(n)
            acc += len(d[n]["cases"])
        else:
            held.append(n)

    def counts(servers):
        c = collections.Counter(case["risk"] for n in servers for case in d[n]["cases"])
        return dict(sorted(c.items()))

    return {
        "seed": SEED,
        "train_frac_target": TRAIN_FRAC,
        "source": "MCPTox-Benchmark@f85189f9 response_all.json (valid cases only)",
        "train_servers": sorted(train),
        "heldout_servers": sorted(held),
        "n_cases": {"train": acc, "heldout": total - acc},
        "n_authentic_tools": {"train": sum(len(d[n]["authentic_tools"]) for n in train),
                              "heldout": sum(len(d[n]["authentic_tools"]) for n in held)},
        "risk_counts": {"train": counts(train), "heldout": counts(held)},
    }


def load_split() -> dict:
    return json.loads(OUT.read_text())


if __name__ == "__main__":
    s = make_split()
    OUT.write_text(json.dumps(s, indent=2) + "\n")
    print(json.dumps({k: s[k] for k in ("n_cases", "n_authentic_tools")}, indent=1))
    cats = sorted(set(s["risk_counts"]["train"]) | set(s["risk_counts"]["heldout"]))
    print(f"{'risk category':28s} {'train':>6s} {'heldout':>8s}")
    for c in cats:
        print(f"{c:28s} {s['risk_counts']['train'].get(c, 0):6d} {s['risk_counts']['heldout'].get(c, 0):8d}")
    print("train servers:", len(s["train_servers"]), " heldout servers:", len(s["heldout_servers"]))
