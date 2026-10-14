# Slide notes for the Phase-2 review (source material for the PPT)

All numbers: preliminary, single run, model qwen3:8b via Ollama on an RTX A2000 12 GB. Always show n.
Numbers come from `results/results.md` / `results/results.csv`, Demo 3 from `recordings/demo3/`.

## Built (works today, verified by tests or runs)
- Inline MCP proxy (stdio): MCP server to the agent, MCP client to the real server. Filters every `tools/list`, blocks calls to removed tools.
- L1 provenance pinning: canonical JSON → SHA-256, TOFU pin store, any change = mismatch, unified diff logged,
  re-approval only via `gateway pin approve`. (Demo 1, pytest)
- L2 capability consistency: 5 categories (filesystem, network, credentials, subprocess, email), patterns in YAML with a
  `source` per pattern (qsag-core 0.2.2, Cisco mcp-scanner @5d147dc, MCPTox train split). Flags when implied ⊄ declared. (Demo 2, pytest)
- Decision ladder with K=2: remove tool / quarantine server / remove until re-pin. Every removal has a one-sentence reason.
- Live agent (Demo 3): qwen3:8b with native tool-calling over MCP. Gateway OFF: canary leaked 10/10 runs.
  Gateway ON: 0/10 (n=10 per mode, temperature 0.7, seeds 0–9, one scenario written by us).
- Evaluation pipeline on MCPTox (Demo 4): grouped-by-server split, stratified held-out sample, resumable runner,
  deterministic judge checked against MCPTox's own labels, bootstrap 95% CIs.
- 17 pytests passing.

## Next (post-review, from CLAUDE.md)
- L3 semantic classifier (DeBERTa/E5 fine-tune on MCPTox train split, class-imbalance handling): targets the
  parameter-tampering / information-manipulation attacks that L2's vocabulary misses.
- L4 LLM arbitrator. Adaptive attacker. Compound / multi-step attacks. Instruction-file track.
- Multi-seed runs + McNemar, a second local model, the full 1,348-case run, third-party baseline scanners.
- Reduce L2 false positives (Commander quarantine; tools whose descriptions mention files/commands they legitimately handle).

## Demo order for the review
1. `scripts/demo1_rugpull.sh`: rug-pull caught, diff shown.
2. `scripts/demo2_mismatch.sh`: get_weather(city) removed with reason; get_forecast still works.
3. `scripts/demo3_live.sh`: OFF leaks the canary, ON blocks it. Fallback: `less -R recordings/demo3/terminal_10x10.log`.
4. Numbers slide from results.md.

## Claims audit: what would not survive a hard question, and the honest wording
| Risky claim | Honest wording |
|---|---|
| "The gateway stops tool poisoning." | "On MCPTox held-out, L1+L2 removed the poisoned tool in 157/498 cases (31.5%); most parameter-tampering attacks are missed." |
| "Demo 3 shows 100% protection." | "In our one fixture scenario, the canary leaked in 10/10 runs without the gateway and 0/10 with it (n=10 per mode)." Never say 100%. |
| "L2 is robust to paraphrase." | "L2 is deterministic and auditable; wording outside the taxonomy's vocabulary can evade it." |
| "FPR is 2.3%." | Headline is all 353 authentic tools: 24/353 = 6.8% (tool level), 1/45 servers quarantined. 2.3% is held-out servers only (3/128). |
| "L1 contributes to the MCPTox numbers." | It does not: every MCPTox tool is first sight, so L1 only pins. L1 is evidenced by Demo 1 only. |
| "ASR measured exactly as in MCPTox." | Same prompts and protocol, but a local quantised model and our deterministic judge (held-out agreement 88.9% with MCPTox labels, Think mode; it under-counts Success). |
| "Latency is negligible." | "p95 of L1+L2+ladder per tools/list: 8.2 ms first sight (incl. pin write), 5.7 ms when pinned (n=2,250 each; re-measured 2026-10-14, varies run to run); excludes upstream round trip." |
| "Hard negatives handled." | "22/161 trigger-word tools removed (13.7%): a weakness, reported as a stress test." |
| Thesis targets (≥30 pp ASR reduction, ≤1% FPR) | Do not claim them. Report measured values only. |

## ASR (held-out n=300 stratified, qwen3:8b think=on, single run)
- No defense 59/300 = 19.7% (CI 15.3–24.3%) → gateway 37/300 = 12.3% (CI 8.7–16.3%). ΔASR 7.3 pp (CI 3.3–11.3 pp).
- Macro over 10 categories: 21.7% → 10.6%.
- Worse with gateway in 2 categories: Instruction Tampering 4→6 /16, Service Disruption 7→8 /54 (false-positive removals change the model's choices).
- Our judge under-counts Success (88.9% held-out agreement); 39/600 responses hit the token cap.
- MCPTox's own Qwen3-8b-Think label on the same cases: 29.0% (n=255): sanity check only.
