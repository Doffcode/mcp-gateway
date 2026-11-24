---
title: "CA649 Review III · Viva brief"
subtitle: "Pre-Execution Metadata Integrity for Model Context Protocol Tools"
papersize: a4
fontsize: 10.5pt
mainfont: "Times New Roman"
margin:
  x: 19mm
  y: 16mm
---

**Opening.** An inline gateway checks MCP tool descriptions and schemas before the agent receives them. L1 detects changes after pinning. L2 and the decision ladder enforce admission. L3 and L4 report advisory findings.

**If L3 flagged 497/498 poisoned examples, why does it stay advisory?** The benchmark had no reconstructed arguments in 492/498 poisoned cases and 8/128 authentic tools. All 340 additional poisoned flags came from that subset. On external authentic listings L3 added 2/278 flags, both from 12 served zero-parameter tools. We still need independent labeled data with populated schemas and a paired agent study with an L3 policy. *Evidence: frozen results and ablations in the thesis screening table; external utility table.*

**What reduced attack success in the paired experiment?** Qwen3 8B with thinking enabled went from 59/300 to 37/300 judged successes, down 7.3 percentage points (95% paired bootstrap interval, 3.3–11.3). Fresh pin stores meant L1 only pinned. The change reflects L2 and the ladder. *Evidence: 300 paired model-response records and the thesis paired-result table.*

**Why were there successes after filtering?** Of 37 gateway-side successes, 28 occurred while the poisoned tool was still served and nine were judged successful after removal. The evaluator judges model text. Those nine cases need adjudication, and the replay has no observed runtime side effect. *Evidence: saved pair records joined with their removal decisions.*

**What does L1 prove?** It detects a metadata change at a subsequent listing for a pinned tool. We show the stored fingerprint, diff, withheld tool, and explicit reapproval on a local fixture. The first pin establishes a reference for later listings. *Evidence: metadata-change fixture and integration test.*

**What is the availability cost?** The baseline removed 3/128 authentic held-out tools. In the external cohort it removed 56/334 authentic tools, with 52 removals from three quarantines. Measured baseline overhead on the lab PC was 8.24 ms at p95 on first sight over 2,250 listings, excluding transport. *Evidence: static availability, external utility, and overhead tables.*

**What does L4 prove?** The local reviewer returned an evidence-grounded verdict on four selected examples: flagged on altered Weather and low risk on Forecast, Contentful, and Clarity. This shows the workflow. Accuracy and impact on attack success require a representative evaluation. *Evidence: four local reviewer records and thesis L4 table.*

**Two-minute demo.** Weather only, gateway in path. Show **2 offered → 1 available** and the L2 decision. Manually request removed `get_weather` and point to rejection before forwarding. Send the prefilled five-day forecast in Agent Chat and point to the `get_forecast` call and the fixture's tool response. Show L4 if time permits. With Ollama offline, make the approved forecast call manually.
