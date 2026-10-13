"""Demo 4 runner: MCPTox ASR without vs with the gateway, one local model (Ollama), resumable.

Protocol = MCPTox's own: single turn, its system prompt (tool list as text, poisoned tool inserted) + its query;
the model answers with one JSON tool call; `eval.judge` labels the response deterministically.

Gateway condition: the server's tool list (authentic tools + the poisoned tool) goes through the real
L1 (fresh pin store, so every tool is first sight = TOFU pin) -> L2 -> decision ladder from src/gateway.
Removed tools' blocks are cut out of the system prompt (all of them if the server is quarantined).
If the gateway removes nothing, the input is byte-identical to the no-defense input and that result is reused.

Every (case, condition) result is appended to var/eval/<run>.jsonl; re-running skips finished pairs.

  uv run python -m eval.run_mcptox --time 5            # seconds per case, both think modes
  uv run python -m eval.run_mcptox --n 150 --think off # stratified held-out sample
"""

import argparse
import collections
import json
import random
import tempfile
import time
from pathlib import Path

from gateway.config import ROOT
from gateway.l1_pins import PinStore
from gateway.l2_capability import L2Analyzer
from gateway.ladder import decide

from .judge import judge
from .mcptox_ingest import RAW, load
from .split import SEED, load_split

OUT_DIR = ROOT / "var" / "eval"
NUM_CTX = 16384  # Ollama defaults to 4096, which would silently truncate long MCPTox prompts
UNLOAD_EVERY = 25  # model calls between prompt-cache flushes
FOOTER = "\nChoose the appropriate tool based on the user's question"


def local_cfg() -> dict:
    import yaml

    p = ROOT / "config.local.yaml"
    raw = (yaml.safe_load(p.read_text()) or {}) if p.exists() else {}
    return {"model": raw.get("model", "qwen3:8b"), "ollama_host": raw.get("ollama_host", "http://localhost:11434")}


def gateway_view(server: str, authentic: list[dict], poisoned: dict, k: int, l2) -> dict:
    """Run L1 + L2 + ladder exactly as the proxy does for one tools/list of this server."""
    tools = authentic + [poisoned]
    names = [t["name"] for t in tools]
    with tempfile.TemporaryDirectory() as d:
        pins = PinStore(Path(d) / "pins.json")
        l1 = {t["name"]: pins.check(server, t) for t in tools}
    flags = {t["name"]: l2(t) for t in tools}
    dec = decide(server, names, l1, flags, k)
    return {"removed": sorted(dec.removed), "quarantined": dec.quarantined,
            "poison_removed": poisoned["name"] in dec.removed,
            "reasons": {n: dec.removed[n] for n in sorted(dec.removed)}}


def _cut_tool(text: str, name: str) -> str | None:
    """Cut the `Tool: <name>` block up to the next tool block or the instruction footer."""
    start = text.find(f"Tool: {name}\n")
    if start < 0:
        return None
    nxt = [i for i in (text.find("\nTool: ", start + 1), text.find(FOOTER, start + 1)) if i >= 0]
    return text[:start] + text[min(nxt) + 1 if nxt else len(text):]


def cut_blocks(system: str, poisoned_text: str, removed: set[str], poisoned_name: str) -> str:
    """Remove the poisoned block (MCPTox text; verbatim when possible) and any removed authentic tool blocks."""
    out = system
    if poisoned_name in removed:
        pt = poisoned_text.strip()
        if pt in out:
            out = out.replace(pt, "", 1)
        else:
            # some MCPTox prompts store newlines escaped / re-wrapped: fall back to the block boundaries
            cut = _cut_tool(out.replace("\\n", "\n"), poisoned_name)
            assert cut is not None, f"poisoned block {poisoned_name!r} not found"
            out = cut
    for name in removed - {poisoned_name}:
        out = _cut_tool(out, name) or out
    return out


def sample_cases(cases: list[dict], n: int, seed: int = SEED) -> list[dict]:
    """Proportional stratified sample by risk category (natural distribution), fixed seed."""
    if n >= len(cases):
        return sorted(cases, key=lambda c: c["id"])
    by = collections.defaultdict(list)
    for c in sorted(cases, key=lambda c: c["id"]):
        by[c["risk"]].append(c)
    rng = random.Random(seed)
    quota = {r: n * len(v) / len(cases) for r, v in by.items()}
    take = {r: int(q) for r, q in quota.items()}
    for r in sorted(quota, key=lambda r: quota[r] - take[r], reverse=True)[: n - sum(take.values())]:
        take[r] += 1  # largest remainder
    out = []
    for r in sorted(by):
        out += rng.sample(by[r], take[r])
    return out


class Model:
    def __init__(self, think: bool, num_predict: int):
        import ollama

        cfg = local_cfg()
        self.name = cfg["model"]
        self.client = ollama.Client(host=cfg["ollama_host"])
        self.think = think
        self.num_predict = num_predict
        self.calls = 0

    def _unload(self) -> None:
        # Ollama's prompt cache grows in host RAM; on the 15 GB lab PC it got OOM-killed after ~80 calls.
        try:
            self.client.generate(model=self.name, keep_alive=0)
        except Exception:
            pass

    def __call__(self, system: str, query: str) -> dict:
        self.calls += 1
        if self.calls % UNLOAD_EVERY == 0:
            self._unload()
        for attempt in range(6):
            try:
                t0 = time.perf_counter()
                r = self.client.chat(model=self.name, think=self.think,
                                     messages=[{"role": "system", "content": system},
                                               {"role": "user", "content": query}],
                                     options={"temperature": 0, "seed": SEED, "num_predict": self.num_predict,
                                              "num_ctx": NUM_CTX})
                break
            except Exception as e:  # server restarted (e.g. OOM): wait for systemd, then retry the same call
                if attempt == 5:
                    raise
                print(f"   ollama error ({type(e).__name__}); retry {attempt + 1}/5 in 15s", flush=True)
                time.sleep(15)
        return {"response": r.message.content or "", "thinking_chars": len(r.message.thinking or ""),
                "done_reason": r.done_reason, "eval_count": r.eval_count, "prompt_eval_count": r.prompt_eval_count, "seconds": time.perf_counter() - t0}


def run(cases: list[dict], data: dict, raw: dict, model: Model, out: Path, k: int) -> None:
    l2 = L2Analyzer.from_dir(ROOT / "taxonomy")
    done = set()
    if out.exists():
        done = {(r["id"], r["condition"]) for r in map(json.loads, out.read_text().splitlines())}
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a") as f:
        for idx, c in enumerate(cases, 1):
            s = c["server"]
            auth = data[s]["authentic_tools"]
            dd = raw[s]["malicious_instance"][int(c["id"].split("#")[1])]["datas"][0]
            gv = gateway_view(s, auth, c["poisoned_tool"], k, l2)
            gw_system = cut_blocks(c["system_prompt"], dd["poisoned_tool"], set(gv["removed"]), c["poisoned_tool"]["name"])
            base = {"id": c["id"], "server": s, "risk": c["risk"], "paradigm": c["paradigm"], "model": model.name,
                    "think": model.think, "mcptox_label_qwen3_8b": dd["label"].get(
                        "Qwen3-8b-Think" if model.think else "Qwen3-8b-No-Think")}
            nd = None
            for cond, system in (("no_defense", c["system_prompt"]), ("gateway", gw_system)):
                if (c["id"], cond) in done:
                    continue
                if cond == "gateway" and system == c["system_prompt"]:
                    if nd is None:
                        prev = [json.loads(x) for x in out.read_text().splitlines()]
                        nd = next(r for r in prev if r["id"] == c["id"] and r["condition"] == "no_defense")
                    res = {k2: nd.get(k2) for k2 in ("response", "thinking_chars", "done_reason", "eval_count", "prompt_eval_count")}
                    res["seconds"] = 0.0
                    res["reused_no_defense"] = True
                else:
                    res = model(system, c["query"])
                    res["reused_no_defense"] = False
                label = judge(res["response"], c["poisoned_tool"], c["query"],
                              [] if gv["quarantined"] and cond == "gateway" else auth)
                rec = {**base, "condition": cond, **res, "label": label, "success": label == "Success", "gateway": gv}
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                f.flush()
                if cond == "no_defense":
                    nd = rec
                print(f"[{idx}/{len(cases)}] {c['id']:28s} {cond:10s} {label:16s} {res['seconds']:6.1f}s", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=0, help="stratified held-out sample size")
    ap.add_argument("--think", choices=["on", "off"], default="off")
    ap.add_argument("--time", type=int, default=0, help="only time this many cases per think mode")
    ap.add_argument("--num-predict", type=int, default=4096)
    ap.add_argument("--k", type=int, default=2)
    a = ap.parse_args()
    data = load()["servers"]
    raw = json.loads(RAW.read_text())["servers"]
    held = [c for s in load_split()["heldout_servers"] for c in data[s]["cases"]]
    if a.time:
        for think in (False, True):
            m = Model(think, a.num_predict)
            cs = sample_cases(held, a.time, seed=SEED + 1)  # timing sample, separate from the eval sample
            out = OUT_DIR / f"timing_{'think' if think else 'nothink'}.jsonl"
            out.unlink(missing_ok=True)
            run(cs, data, raw, m, out, a.k)
            rs = [json.loads(x) for x in out.read_text().splitlines()]
            sec = [r["seconds"] for r in rs if not r["reused_no_defense"]]
            print(f"think={think}: {sum(sec) / len(sec):.1f} s per model call (n={len(sec)} calls), "
                  f"{sum(sec) / a.time:.1f} s per case incl. gateway condition")
        return
    m = Model(a.think == "on", a.num_predict)
    cases = sample_cases(held, a.n)
    out = OUT_DIR / f"mcptox_heldout_n{len(cases)}_think-{a.think}.jsonl"
    print(f"{len(cases)} held-out cases -> {out}")
    run(cases, data, raw, m, out, a.k)


if __name__ == "__main__":
    main()
