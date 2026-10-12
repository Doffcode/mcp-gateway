# MCP Metadata Integrity Gateway

M.Tech thesis project (NIT Trichy): a deterministic-first gateway that sits between an
agent client and MCP servers and blocks poisoned tool metadata *before* the agent sees it.
Owner: Shivansh. If something below is ambiguous or missing, ASK — do not invent a decision.

## Situation and hard constraints
- 2-day sprint to a Phase-2 review (changed from 5 days on 2026-10-12). Goal is a **demo-first prototype**:
  4 things that visibly work. After the review there is ~1 month to finish. Do NOT build post-review items
  now (see "Out of scope").
- No hand-crafted datasets. Generate with an LLM only when something is genuinely necessary;
  otherwise skip it and say so.
- Local models only (Ollama, lab desktop RTX A2000 12 GB). No API models, no paid calls.
- Test ONLY against our own fixture servers and released MCPTox data. Never probe real third-party MCP servers.
- L1 and L2 are deterministic: **no LLM calls, no network, no randomness** inside them.
- Python 3.11+, official `mcp` Python SDK, pytest. Fixed seeds everywhere. Structured JSON logs.
- The `mcp` SDK is v2 (`mcp>=2.3,<3`): FastMCP is now `mcp.server.mcpserver.MCPServer`. Exact versions are locked in `uv.lock`.

## Two-machine workflow
- Laptop (no GPU) for deterministic work; lab PC (RTX A2000) for LLM runs.
- Git is the only shared state: pull before starting, commit + push before switching machines.
- `PROGRESS.md` is the handoff log. Read it with this file at the start of every session and update it at the end.
- Fresh machine: `scripts/setup.sh` (uv sync + MCPTox fetch with sha256 check), then `uv run pytest -q`.
- Per-machine settings go in `config.local.yaml`; runtime state goes in `var/` (both gitignored). Raw MCPTox data is never committed (it has no license).

## Architecture
Inline **proxy**, not an optional tool. The agent's MCP server address points at the gateway;
the gateway is an MCP *server* to the agent and an MCP *client* to the real server (stdio first).
On every `tools/list`, for each tool: L1 -> L2 -> decision ladder -> filtered list returned to agent.
Every removal is logged with a one-sentence human-readable reason (which layer, which rule).

### L1 — provenance pinning
- Canonical JSON of `{name, description, inputSchema}` -> SHA-256. Canonicalize (sorted keys, stable whitespace) so hashing is stable.
- First sight: pin (TOFU) into a local pin store (JSON or SQLite). Later sight: compare.
- **Any hash change = mismatch.** No semantic-diff threshold, no auto-approve. Log a unified diff of old vs new.
- Re-approval is an explicit CLI command (`gateway pin approve <server> <tool>`), never automatic.

### L2 — capability consistency
- Taxonomy of 5 categories: `filesystem`, `network`, `credentials`, `subprocess`, `email`.
- Each category has three pattern lists: **actions** (verbs), **targets** (nouns/paths/resources), **schema_hints** (parameter names/types).
  Patterns are keyword/regex. Seed them from public rule sets (qsag-core **0.2.2**, since 0.2.3 ships empty
  pattern lists; Cisco mcp-scanner YARA rules @5d147dc) and MCPTox *train-split* cases only.
  Every pattern records its `source` in the YAML.
- `implied` = categories found in the description (+ tool name). `declared` = categories justified by the input schema (param names, types, param descriptions).
- **Flag a tool if `implied` is not a subset of `declared`.** Each flag records category, matched pattern, and the missing schema justification.
- L2 is NOT exhaustive and must never be described as "paraphrase-immune". Correct wording:
  "deterministic and auditable; wording outside the taxonomy's vocabulary can evade it."
- Keep the pattern lists in data files (YAML), not buried in code, so they are reviewable.

### L3 — semantic classifier (DEFERRED to post-review)
DeBERTa-base or E5-base fine-tune on MCPTox **train split** only, with class-imbalance handling. Never touch the held-out split during training or tuning.

### L4 — LLM arbitrator
Later. Do not build in the sprint.

## Decision ladder (config: `K = 2`)
| Situation | Action |
|---|---|
| L2 flags one tool (first sight) | Remove that tool from `tools/list`, log reason |
| L2 flags >= K tools in the same server | Quarantine the whole server |
| L1 mismatch, L2 clean (e.g. legit version bump) | Remove just that tool until re-pin approved; log diff |
| L1 mismatch AND L2 flags the new version | Quarantine the whole server |

## Four demos (acceptance criteria)
1. **Rug-pull catch (L1):** server serves a clean description, it gets pinned, then the description silently changes. Gateway blocks it and prints the diff. Deterministic; must pass in a pytest.
2. **Capability mismatch (L2):** a tool like `get_weather(city)` whose description implies filesystem/credential access that its schema does not declare. Gateway removes it and prints the reason; other tools keep working. Must pass in a pytest.
3. **Before/after, live:** local-model agent loop (Ollama tool-calling) against a poisoned fixture plus a canary file. Gateway OFF: canary content leaks. Gateway ON: attack blocked. LLM behaviour is non-deterministic: find a scenario that triggers reliably, save a backup recording.
4. **Numbers slide:** on a stratified MCPTox sample with 1 local model — ASR without vs with gateway, FPR on the 353 authentic tools, p95 latency for L1+L2. (L3 is deferred.) Bootstrap 95% CIs (case-level, 1,000 resamples, single run) are allowed. Always print `n`, never print a number without its sample size.

## Data rules (locked)
- MCPTox cases used **as-is**. No synthetic variants. Natural category distribution. Report micro- AND macro-average, plus a per-category table.
- Train/eval split is **grouped by server** (never random). L2 patterns are tuned on the train split only.
- Hard negatives = filter of the 353 authentic tools by a trigger-word list. That list must come from a source independent of L2's patterns and be frozen in git BEFORE L2 is built. Report hard-negative results as a separate stress test with the rule-of-three upper bound, not as the headline FPR.
- Headline FPR is measured on all 353 authentic tools.
- Compound / multi-step attacks are in thesis scope but deferred to post-review.
- MCPTox: 1,348 instances, 36 flagged `wrong_data` → **1,312 valid** cases used. 353 authentic tools = the `tool_names` lists.
- Split: grouped by server, seed 20261012, ~60% of cases in train (29 servers / 814 cases; held-out 16 / 498).
  "Other" (n=4) falls entirely in train; reported as n=0 on held-out.
- Hard-negative triggers: MITRE ATT&CK v19.2 technique names (frozen in commit facb89f, before L2).

## Fixtures (we generate the code; small and local)
Four servers: weather (clean + poisoned variants), filesystem (legit `read_file(path)`), rug-pull server (changes its own description after approval, switchable by a control file), and a benign server whose tools use trigger words. Canary secret is a dummy file in a sandbox dir, never a real credential.

## Out of scope for the sprint (do not build, do not scaffold)
L3 classifier, L4 arbitrator, adaptive attacker, multi-seed runs/McNemar, a second local model, API models, full 1,348-case run, third-party baseline scanners, compound-attack set, instruction-file track (CLAUDE.md/hooks poisoning), Docker/packaging.

## Honesty rules for anything that ends up on a slide
- Label every result "preliminary, n = ..." and state the model used.
- Do not claim the thesis targets (>=30 pp ASR reduction, <=1% FPR); report what was measured.
- Never report 100% on anything. Report failures and misses.
- Do not mock a demo and call it working. If a demo does not work, say so.

## Working agreements
- Start each session in plan mode; show the plan; wait for approval before editing.
- End each session by updating PROGRESS.md and pushing.
- Commit after each working demo. Run tests yourself before saying something works.
- Keep this file current when a decision changes; propose the edit, do not silently drift.
