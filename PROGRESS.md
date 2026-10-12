# PROGRESS: handoff log (read with CLAUDE.md at the start of every session, on either machine)

Sync rule: git is the only shared state. Pull before you start; commit + push before you switch machines.
Setup on a fresh machine: `git clone … && cd mcp-gateway && scripts/setup.sh && uv run pytest -q`.

## Timeline / decisions (2026-10-12)
- Review is 2 days away (not 5). Day 1 = laptop (deterministic parts). Day 2 = lab PC (LLM runs).
- L3 deferred to post-review. Bootstrap 95% CIs (case-level, single run) approved.
- mcp SDK is v2 (`mcp>=2.3,<3`): FastMCP is now `mcp.server.mcpserver.MCPServer`; high-level `mcp.Client`.
- Upstream client runs with `cache=None` and `cache_mode="bypass"` so every tools/list really reaches the server.
- TOFU pins on first sight regardless of L2 (literal reading of CLAUDE.md). A flagged tool stays removed by L2 anyway.

## MCPTox recon (Day 0)
- Source: github.com/zhiqiangwang4/MCPTox-Benchmark @ f85189f9 (no explicit license → not committed; `scripts/fetch_mcptox.sh`).
- `response_all.json`: 45 servers; per server `tool_names`, `clean_system_promot` (authentic tools as TEXT),
  `malicious_instance[]` with `poisoned_tool` (text), `metadata.{paradigm, security risk}`, `wrong_data`, `datas[1]` (query).
- 1,348 instances, 36 `wrong_data` → **1,312 valid**. 353 authentic tools. Grouping by server is possible (server key).
- Risk categories (valid): Privacy Leakage 273, Information Manipulation 269, Service Disruption 196, Infrastructure Damage 122,
  Data Tampering 117, Credential Leakage 115, Code Injection 63, Instruction Tampering 57, Financial Loss 55, Message Hijacking 41, Other 4.
- Paradigms: Template-1 208, Template-2 519, Template-3 585.
- CAVEAT for L2: schemas exist only as text ("Arguments: - name: desc (required)"), with no JSON types. Poisoned tools are
  decoys whose description tells the agent to misuse *other* legitimate tools; many have "No arguments".

## Sources pinned for L2 (all tagged per pattern in taxonomy/*.yaml)
- qsag-core **0.2.2** from PyPI (Apache-2.0). NOTE: latest 0.2.3 ships EMPTY pattern lists ("inactive"), so we use 0.2.2.
- Cisco mcp-scanner YARA rules @ 5d147dc (credential_harvesting, data_exfiltration, command_injection, system_manipulation, tool_poisoning).
- MCPTox TRAIN split vocabulary only. Held-out never read for tuning.
- Hard negatives: MITRE ATT&CK v19.2 (attack-stix-data @ 6cda5ad8), 204 words, frozen in commit facb89f BEFORE L2.

## Split (data/split.json, seed 20261012, grouped by server, train target 60% of cases)
- train: 29 servers, 814 cases, 225 authentic tools. held-out: 16 servers, 498 cases, 128 authentic tools.
- "Other" (n=4) has no held-out cases.

## L2 on TRAIN (preliminary, n=814 cases / 225 authentic tools); `uv run python -m eval.l2_train_report`
- micro recall 41.8% (340/814), macro 44.6% over 11 categories. Strong: Message Hijacking 29/29, Credential Leakage 82/89,
  Code Injection 41/54. Weak by design: Information Manipulation 27/155, Service Disruption 12/106, Financial Loss 0/14
  (parameter tampering of *other* legitimate tools implies no filesystem/network/credentials/subprocess/email capability).
- FP 8/225 train authentic tools. 4 are in Commander (descriptions cross-reference 'execute_command'), so at K=2 the
  Commander server would be QUARANTINED: a real server-level false positive to report.
- Design choice tuned on train: snake/camel-case splitting of tool references (+14 pp recall, +4 FP).

## Status
- [x] Step 0: remote `origin` = github.com/Doffcode/mcp-gateway (branch `master`), uv env, setup/fetch scripts
- [x] Fixtures: weather (clean/poisoned), filesystem (sandboxed read_file), rugpull (control file clean/bump/evil), benign
- [x] Proxy + L1 + `gateway pin approve|list` + ladder (pure fn, K from gateway.yaml)
- [x] Demo 1: `scripts/demo1_rugpull.sh` (with L2 active, the evil change escalates to L1+L2 quarantine; still shows the diff)
- [x] Hard-negative list frozen (ATT&CK)
- [x] MCPTox ingest (`eval/mcptox_ingest.py`) + grouped split (`eval/split.py`)
- [x] L2 taxonomy + analyzer; Demo 2: `scripts/demo2_mismatch.sh`
- [x] `uv run pytest -q` → 15 passed (Demo 1, Demo 2, ladder rows, canonical hashing, benign no-FP)
- [ ] Day 2 (lab PC): Demo 3 agent loop (Ollama), Demo 4 numbers (ASR w/o vs with gateway, FPR on 353, hard negatives, p95)

## Next step (Day 2, lab PC)
`git pull && scripts/setup.sh && uv run pytest -q`, then build `agent/loop.py` (Ollama tool-calling over MCP),
run 10x gateway OFF / 10x ON against poisoned weather + filesystem + canary, then the Demo 4 runner.

## Proposed CLAUDE.md edits (not applied; owner decides)
- Timeline: 2-day sprint; L3 deferred to post-review; bootstrap CIs (case-level, single run) allowed.
- Note mcp SDK v2 and the two-machine workflow (PROGRESS.md handoff, setup.sh).
- Note qsag-core version pin (0.2.2) and that its pattern count is not 26 in that release.
