# Sprint prompts for Claude Code

How to use: start `claude` in plan mode (`claude --permission-mode plan`, or press Shift+Tab until the
status bar shows `⏸ plan mode on`). Paste one prompt. Read the plan it proposes. Approve only when it matches
CLAUDE.md. After the day's acceptance check passes, commit, then `/clear` before the next day's prompt
(CLAUDE.md reloads each session, so nothing important is lost).

---

## Day 0 — read-only recon (1–2 hours, no building)

> Read CLAUDE.md fully. Do NOT write any code yet. Do two research tasks and report back:
> 1. Find the released MCPTox data (paper arXiv:2508.14925; look for its GitHub repo or dataset link). Tell me: where it lives, the file format, which fields exist (tool metadata, injected payload, risk category, server name, user query, expected malicious action), how many cases and servers, and whether cases can be grouped by server. If the data is NOT available or incomplete, say so plainly and propose the smallest LLM-generation fallback — I will decide.
> 2. Read the MCP-GuardBench repo (github.com/Manishmaurya89/mcp-guardbench). Summarize in 10 lines how its fixtures are structured, and in 5 lines how it differs from our design (inline proxy with L1 pinning + L2 capability consistency, evaluated by ASR reduction).
> Also confirm `python3 --version`, whether Ollama is installed, and that `ollama list` shows at least one model. Report only; change nothing.

Acceptance: you know whether MCPTox data is usable, and whether Ollama is ready.

---

## Day 1 — skeleton, fixtures, L1 (Demo 1)

> Using CLAUDE.md, set up the repo (git init, pyproject, pytest) and build: (a) the four fixture MCP servers described in CLAUDE.md using the official `mcp` Python SDK over stdio; (b) a pass-through gateway proxy that is an MCP server to the client and an MCP client to a real server, forwarding `tools/list` and `tools/call` unchanged; (c) L1: canonical hashing, TOFU pin store, mismatch detection with a logged diff, and the `gateway pin approve` CLI command; (d) a pytest that reproduces Demo 1 (clean -> pinned -> silently changed -> blocked with diff). Propose the repo layout in the plan first. Keep L1 free of any LLM or network calls.

Acceptance: `pytest` passes, and `scripts/demo1_rugpull.sh` shows the block with a diff.

---

## Day 2 — L2, ladder (Demo 2), MCPTox ingest

> Build L2 and the decision ladder exactly as in CLAUDE.md. Pattern lists go in YAML files (`taxonomy/*.yaml`) with the three lists per category. Seed them only from public rule sets and from the MCPTox TRAIN split, never the held-out split. First, write the frozen hard-negative trigger-word list from an independent source and commit it before touching L2. Then: implement L2, wire the ladder with K from config, and add a pytest for Demo 2 (poisoned weather tool removed with a reason, other tools still served). Then write the MCPTox ingest: load the cases per the Day-0 findings, build the grouped-by-server train/held-out split (fixed seed, saved to disk), and report per-category counts. Show me the plan first, including which pattern sources you intend to use.

Acceptance: Demo 2 pytest passes; split file exists; L2 recall per category on the TRAIN split printed.

---

## Day 3 — agent loop (Demo 3) and L3

> Two parts. Part A: write a minimal agent loop that uses Ollama tool-calling with one local model (tell me which models are installed and pick the smaller one that supports tools) as an MCP client. It must run in two modes: gateway OFF (agent connects straight to the poisoned fixture) and gateway ON (through our proxy). Build the canary scenario and a checker that detects whether canary content left the sandbox. Run each mode 10 times and report how often the attack succeeds so I can pick a reliable scenario. Part B: L3 fine-tuning script (DeBERTa-base or E5-base) on the MCPTox TRAIN split only, grouped split from Day 2, class-imbalance handling, fixed seed; evaluate once on the held-out split and report P/R/F1 with n. Do not tune on held-out. Plan first.

Acceptance: a mode-OFF vs mode-ON table with counts out of 10; L3 held-out metrics printed with n.

---

## Day 4 — numbers (Demo 4) and recording

> Build a resumable, seed-pinned eval runner (cache every result to disk so a crash or Ctrl-C loses nothing). On a stratified sample of the MCPTox held-out split with one local model, run: no defense, L1+L2, L1+L2+L3. Report ASR for each, delta-ASR, FPR on all 353 authentic tools, the hard-negative stress test with its rule-of-three upper bound, and p95 latency of L1+L2 (cache hit and miss). Print bootstrap 95% CIs (1,000 resamples) and always print n. Output one CSV plus a short results.md that labels everything "preliminary". First measure seconds per case on 5 cases and tell me the sample size you can afford in the time I have before choosing it.

Acceptance: `results.csv`, `results.md`; every number has n and a CI.

---

## Day 5 — polish and rehearsal

> Do not add features. (1) Make each of the four demos runnable with one command and write `DEMO.md` with the exact commands and expected output. (2) Re-run Demos 1 and 2 pytests and the end-to-end smoke run. (3) Write a "Built / Next" list using only what actually works today, plus the post-review items from CLAUDE.md. (4) List every claim in results.md that would not survive a hard question, and what the honest wording should be.

Acceptance: all demos run from a clean shell; backup recording of Demo 3 saved.

---

## Tips
- `claude --continue` resumes the last session in this folder; `/resume` lets you pick one.
- If Claude Code starts inventing decisions, say: "That is not in CLAUDE.md — ask me."
- Ask it to run the tests itself and paste the output; do not accept "it should work".
