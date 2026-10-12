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

## Status
- [x] Step 0: remote `origin` = github.com/Doffcode/mcp-gateway (branch `master`), uv env, setup/fetch scripts
- [x] Fixtures: weather (clean/poisoned), filesystem (sandboxed read_file), rugpull (control file clean/bump/evil), benign
- [x] Proxy + L1 + `gateway pin approve|list` + ladder (pure fn)
- [x] Demo 1: `uv run pytest -q` → 6 passed; `scripts/demo1_rugpull.sh` shows block + diff
- [x] Hard-negative trigger list frozen: MITRE ATT&CK v19.2 (user decision), 204 words, `data/hard_negative_triggers.txt`
- [ ] L2 taxonomy + analyzer, Demo 2 test
- [ ] Day 2: MCPTox ingest/split, Demo 3, Demo 4

## Next step
Decide the source of the hard-negative trigger list → commit it → build L2.
