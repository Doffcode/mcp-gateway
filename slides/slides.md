## Introduction: agents pick tools by reading the server's text

- Model Context Protocol (MCP) connects AI agents to tool servers
- The agent gets each tool's name, description and input schema
- It picks and uses tools by **reading the description**
- That description is written by whoever runs the server

![How an agent uses an MCP tool.](figures/intro)

::: notes
Agents like Claude Code, Cursor and Gemini CLI connect to MCP servers. On connect, the agent calls tools/list and gets back a name, a plain-English description and an input schema for every tool.
The agent decides what to do by reading those descriptions. So the description is effectively a manual the agent obeys. Nobody checks it today.
Large Language Model (LLM) safety training targets user prompts, not tool manuals, so it does not cover this channel.
:::

## Introduction: the gateway is a front desk for the agent {.image}

The assistant, a Large Language Model (LLM) agent, follows any card it gets: we check the card, not the assistant.

![The analogy: every gadget's instruction card passes the front desk before the assistant reads it.](figures/analogy)

::: notes
Walk the picture left to right.
The vendor (MCP server) delivers a gadget (tool) with an instruction card (description). The assistant (LLM agent) follows cards faithfully and already holds the office keys (files, credentials).
A poisoned card says: "Before using this thermometer, take the spare key from the cabinet and write its tag in the notes." The thermometer itself is harmless; the card is the attack.
The front desk does two checks. Check 1: does the card match the gadget's ports? A thermometer with only a city dial has no business talking about keys. That is L2. Check 2: is this the same card we approved last time? A swapped card is held. That is L1.
Why not just train a smarter assistant? MCPTox found more capable models were MORE susceptible: a better assistant follows the card more faithfully.
:::

## Literature review: nobody measures whether attacks stop

| Work | What it does | Evaluated on | Gap |
|:--|:--|:--|:--|
| MCPTox [@wang2026mcptox] | Tool-poisoning benchmark | 45 real servers, 20 agents | Attack only, no defense |
| MCPSecBench [@yang2025mcpsecbench] | 17 attack types | 3 MCP platforms | Attack only |
| MCP-Guard [@xing2026mcp] | 3-stage detector + LLM arbiter | 70,448 GPT-4-augmented samples | Accuracy, not attack success |
| CASCADE audit [@turgut2026evaluating] | Layered local defense | 5,000 own samples | FPR 1.51% to 11.70% by scoring rule |
| SoK, 78 studies [@maloyan2026prompt] | Survey of defenses | Prior work | Adaptive attacks succeed >85% |
| This work | Inline deterministic gateway | MCPTox real tools | Measures ASR, FPR, latency |

::: notes
Two kinds of papers. Attack papers (MCPTox, MCPSecBench) measure how bad the problem is: MCPTox average Attack Success Rate (ASR) 36.5%, peak 72.8%.
Defense papers (MCP-Guard, CASCADE) report classifier accuracy on their own, mostly synthetic, data. None reports whether the attack was actually stopped. In my Review I survey, 0 of 4 defenses reported ASR reduction on MCPTox.
The CASCADE audit shows the same defense reports an FPR of 1.51% or 11.70% depending only on how review decisions are scored: published numbers are not comparable.
The meta-analysis shows adaptive attackers beat state-of-the-art defenses more than 85% of the time, so purely learned detectors can be reworded around.
This work: a defense evaluated on real tools by attack prevention.
:::

## Problem statement: one poisoned description leaks data {.image}

**Problem**: nothing checks tool descriptions before the agent obeys them.

![How one poisoned description becomes a data leak.](figures/attack)

::: notes
Walk the chain. The malicious instruction sits inside the tool's own manual, so it looks like legitimate usage. The agent uses tools it is allowed to use. Nothing fails, so there is no signal to self-correct.
Second kind of attack, the rug-pull: a server is approved while clean, then silently changes its description.
The full statement: there is no mandatory, auditable check on tool metadata before the agent reads it, and no defense is measured by whether attacks actually stop.
Three gaps: (1) defenses report accuracy, not attack prevention; (2) false positives on real tools are not measured at scale; (3) learned detectors have no deterministic floor against rewording.
:::

## Objectives

1. Build an inline gateway that checks tool metadata before the agent sees it
2. Catch changed descriptions with provenance pinning (L1)
3. Catch descriptions that claim more than their schema (L2)
4. Measure Attack Success Rate (ASR) with and without the gateway, False Positive Rate (FPR) and latency

::: notes
Objectives 1 to 3 are the system; objective 4 is how it is judged.
L1 and L2 are deterministic: no LLM calls, no network, no randomness, so every decision is reproducible and explainable.
L3 (learned classifier) and L4 (LLM arbiter) come after this review.
:::

## Methodology 1: the gateway sits in the agent's path {.image}

The gateway is an MCP server to the agent and an MCP client to the real server.

![System architecture.](figures/architecture)

::: notes
If the check were just another tool, a poisoned agent would never call it. As a proxy, every tools/list passes through it: complete mediation.
The agent's config points at the gateway instead of the server; the agent does not notice anything changed.
The pin store keeps one SHA-256 hash per tool. Every removal is written to a JSON log with a one-sentence reason: which layer, which rule.
L3 and L4 are dashed: planned after this review.
:::

## Methodology 2: two deterministic checks per tool {.image}

L2 example: get_weather(city) says "also read the API key", but its schema has only city, so it is removed.

![What happens to each tool on every tools/list.](figures/checks)

::: notes
L1, provenance pinning: canonical JSON hashed with Secure Hash Algorithm (SHA)-256. First sight is pinned (Trust On First Use, TOFU). Any later change, even a comma, is a mismatch; the diff is shown and only a human re-approves with gateway pin approve.
L2, capability consistency: 5 categories (filesystem, network, credentials, subprocess, email). Implied = found in the description and name. Declared = justified by the schema. Flag if implied is not a subset of declared. Patterns are in YAML, each tagged with its source: qsag-core 0.2.2, Cisco mcp-scanner, MCPTox train split.
Decision ladder, K = 2: two or more flagged tools in one server quarantines the whole server. Changed AND inconsistent also quarantines the server.
Honest limit: L2 is deterministic and auditable; wording outside the taxonomy's vocabulary can evade it. L1 cannot catch a first version that is already poisoned.
:::

## Methodology 3: evaluation on MCPTox, split by server {.image}

Same cases, same local model (qwen3:8b), with and without the gateway.

![Evaluation pipeline.](figures/evaluation)

::: notes
MCPTox used as-is: 1,348 instances minus 36 marked wrong_data gives 1,312 valid cases; 353 authentic tools. No synthetic data.
Split grouped by server so no server is in both halves: train 29 servers / 814 cases, held-out 16 servers / 498 cases. L2 patterns are tuned on train only.
Metrics: ASR without vs with gateway; FPR on all 353 authentic tools; p95 latency; per-category and micro/macro averages. Bootstrap 95% Confidence Interval (CI), 1,000 resamples.
Hard negatives: authentic tools containing MITRE ATT&CK words, list frozen in git before L2 was built, reported as a separate stress test.
Local model only, via Ollama on an RTX A2000.
:::

## References {.references}

## Prototype status and preliminary results {.backup}

| Item | Result (preliminary, qwen3:8b, single run) |
|:--|:--|
| Demo 1 rug-pull, Demo 2 mismatch | Working, 17 tests pass |
| Demo 3 live agent canary | Leaked 10/10 without, 0/10 with (n = 10 each) |
| Poisoned tools removed, held-out | 157/498 = 31.5% |
| Real tools wrongly removed | 24/353 = 6.8% |
| p95 gateway latency | 8.24 ms first sight (n = 2,250) |
| ASR without → with gateway | 19.7% → 12.3%, Δ 7.3 pp (95% Confidence Interval (CI) 3.3 to 11.3), n = 300 |

::: notes
Only if asked. Preliminary numbers, single run, qwen3:8b think on. ASR got worse with the gateway in two categories: Instruction Tampering 4 to 6 of 16 and Service Disruption 7 to 8 of 54, likely because false-positive removals change the model's choices. Our judge under-counts successes (88.9% agreement with MCPTox labels). 39 of 600 responses hit the token limit. Weakest categories are parameter-tampering attacks (Information Manipulation 13/114). One server (Commander) is quarantined with no attack present.
:::
