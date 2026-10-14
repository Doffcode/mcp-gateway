# Facts for the Review II deck (every number on a slide must be here)

## Background (MCPTox paper, AAAI 2026, arXiv:2508.14925)
- MCPTox: average attack success rate 36.5% across 20 agents; peak 72.8% (o1-mini) [source: ~/Downloads/Cybersecurity research trends and saturated topics in 2026(2).pdf (chat.txt:194-195, 619)]
- MCPTox: more capable models were more susceptible ("inverse scaling") [source: chat.txt:4800-4810]
- MCPTox: 45 servers, 353 authentic tools, 1,348 instances, 36 wrong_data, 1,312 valid [source: PROGRESS.md:16-17]

## Method
- 5 capability categories: filesystem, network, credentials, subprocess, email [source: CLAUDE.md L2 section]
- Decision ladder K = 2 [source: CLAUDE.md decision ladder]
- Pattern sources: qsag-core 0.2.2, Cisco mcp-scanner @5d147dc, MCPTox train split [source: PROGRESS.md:24-27]
- Split: seed 20261012; train 29 servers / 814 cases / 225 authentic tools; held-out 16 servers / 498 cases / 128 authentic tools [source: PROGRESS.md:30-32]
- Bootstrap 95% CI, 1,000 resamples [source: CLAUDE.md demo 4]
- Hard negatives: MITRE ATT&CK v19.2, 204 words, frozen before L2 [source: PROGRESS.md:28]
- Model qwen3:8b via Ollama, RTX A2000 12 GB; num_ctx 16384 [source: PROGRESS.md:61-75]
- Python 3.11+, mcp SDK v2; 17 pytests passing (run 2026-10-14) [source: uv run pytest -q]
- 4 fixture servers [source: PROGRESS.md:47]

## Results (preliminary, single run) [source: results/results.md]
- Demo 3: gateway OFF canary leaked 10/10, ON 0/10; n=10 per mode, temperature 0.7, seeds 0-9 [source: PROGRESS.md:53]
- Poisoned tool removed, held-out: 157/498 = 31.5% (CI 27.5%-35.5%); macro 40.9% over 10 categories
- Credential Leakage 23/26 = 88.5%; Information Manipulation 13/114 = 11.4%; Financial Loss 6/41 = 14.6%
- FPR all authentic tools: 24/353 = 6.8% (CI 4.2%-9.3%); held-out 3/128 = 2.3%
- Servers quarantined without attack: 1/45 (Commander)
- Hard negatives: 22/161 removed = 13.7%
- Latency p95 per tools/list: 11.67 ms first sight, 6.54 ms pinned (n=2,250 each); p50 1.33 / 0.82 ms
- Judge agreement with MCPTox labels, held-out Think: 88.9% (n=425) [source: PROGRESS.md:66]
- ASR held-out n=300 think=on: no defense 59/300 = 19.7% (CI 15.3%-24.3%); gateway 37/300 = 12.3% (CI 8.7%-16.3%); delta 7.3 pp (CI 3.3 to 11.3 pp) [source: results/results.md]
- Instruction Tampering 4/16 -> 6/16; Service Disruption 7/54 -> 8/54; 39/600 truncated [source: results/results.md]
- Latency re-measured 2026-10-14: p95 8.24 ms first sight, 5.72 ms pinned, n=2,250 [source: results/results.md]
- Review I survey: 0 of 4 surveyed defenses reported ASR reduction on MCPTox [source: chat.txt:Q&A numbers cheat-sheet]
- CASCADE audit (arXiv 2604.17125 v3): 5,000-sample corpus; FPR 11.70% vs 1.51% depending on decision convention [source: arXiv abstract]
- MCP-Guard: 70,448 GPT-4-augmented samples, E5 stage 96.01% accuracy, 3 stages [source: arXiv 2508.10991 abstract]
- MCPSecBench: 17 attack types, 3 platforms [source: arXiv 2508.13220 abstract]
- SoK (arXiv 2601.17548): 78 studies, adaptive ASR >85% [source: arXiv abstract]
- MCPTox: 20 agents; meta-analysis of 78 studies: adaptive attack success >85% [source: chat.txt:619, 662]
