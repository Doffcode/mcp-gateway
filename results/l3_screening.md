# L3 metadata screening · 23 November 2026

Preliminary classifier evaluation on MCPTox. Training and threshold selection used five server-grouped folds over 29 servers (814 poisoned examples, 225 authentic tools). The final model was refit on all training servers, then evaluated on the frozen 16-server held-out split. The deployment artifact and machine-readable report are local under `var/l3/`. See [L3 reproduction commands](../DEMO.md#l3-metadata-screening-experiment).

## Model selection

The selection rule maximized flags on poisoned examples missed by direct L2 and still served by the existing gateway. It allowed at most 5% additional flags on the 204 authentic tools that the training baseline served. Ties favored fewer additional authentic flags, then simpler inference.

| Candidate | Additional poisoned flags / 465 served | Additional authentic flags / 204 served |
|---|---:|---:|
| Word and character TF–IDF + logistic regression | 465 | 0 |
| Frozen E5 + logistic regression | 461 | 8 |
| E5 fine-tuned for 1 epoch | 465 | 0 |
| E5 fine-tuned for 2 epochs | 465 | 0 |
| Frozen E5 + sibling tool names | 444 | 10 |

The CPU text classifier won the tie. Its frozen threshold was **0.5436877**. The E5 candidates ran on the RTX A2000 using PyTorch 2.7.1+cu128 and the checkpoint revision recorded in the training code. Only the selected classifier was evaluated on the held-out partition.

## Held-out screening

| Measure | Result |
|---|---:|
| Poisoned examples flagged | 497/498 |
| Authentic tools flagged | 1/128 |
| Precision and recall at the frozen threshold | 99.8% each (497/498) |
| Additional poisoned examples flagged among those the baseline served | 340/341 |
| Additional authentic tools flagged among those the baseline served | 1/125 |
| Authentic tools either removed by the baseline or flagged by L3 | 4/128 |

CPU model load took **25.4 ms**. Warm scoring p95 was **0.77 ms** for one tool and **3.62 ms** for twelve tools, measured over 20 repetitions on the lab PC. These timings cover scoring and exclude MCP transport.

## What the numbers support

- The classifier screened released benchmark metadata. The gateway's enforcement policy was unchanged, and this experiment did not measure attack-success reduction.
- The held-out data has a marked schema imbalance. **492/498 poisoned** examples and **8/128 authentic** tools had no reconstructed arguments. L3 flagged **491/492** and **0/8** in that subset. Among examples with reconstructed arguments it flagged **6/6** poisoned examples and **1/120** authentic tools. There were only six poisoned examples in the latter subset, and L2 had already removed all six. This leaves real-world generalization and additional coverage for schema-bearing examples open.
- No held-out tool matched training metadata exactly or under the case, whitespace, and numeric normalization used here. Different wording can still share a template. The class balance also matters when interpreting precision.
- On the two existing local weather listings, the classifier scored the same weather tool **0.132** with clean metadata and **0.659** with altered metadata. The forecast tool remained below threshold at **0.114** in both runs. The smoke test fetched tool lists only.

## Follow-up diagnostics

The deployment artifact and threshold stayed frozen. The name-and-description-only model was trained using the same five server-grouped folds and selection rule, with its own validation-selected threshold of **0.4851228**. This comparison reused the already-seen held-out partition and is diagnostic. Reserve a fresh set before evaluating any revised classifier.

| Screen | Poisoned flagged | Authentic flagged | Added poisoned flags beyond baseline | Added authentic flags beyond baseline |
|---|---:|---:|---:|---:|
| No reconstructed arguments | 492/498 | 8/128 | 341/341 | 8/125 |
| Name and description only | 493/498 | 12/128 | 337/341 | 12/125 |
| Frozen full-metadata L3 | 497/498 | 1/128 | 340/341 | 1/125 |

The shortcut catches one more case among those the existing gateway serves and flags seven more authentic tools. The name-and-description-only model still catches most cases in this corpus. Together, these results show that wording alone contains strong class cues, while schema information helps the classifier on this dataset. They leave robustness against different kinds of metadata open.

### Local authentic listings

The frozen classifier scored live listings. No tool calls were made. These are convenience samples, with a separate row for newer versions of server families that already appear in MCPTox.

| Cohort | Tools flagged | Servers with flags | Flags among tools with zero parameter properties |
|---|---:|---:|---:|
| Outside MCPTox server families: Time 2026.10.10 and [Playwright 0.0.86](https://github.com/microsoft/playwright-mcp) | 0/27 | 0/2 | 0/2 |
| Owned fixtures: clean weather, benign, and filesystem | 0/7 | 0/3 | — |
| MCPTox server families, local package versions: Git 2026.10.10, Filesystem 2.4.0, Memory 2.2.1 | 0/37 | 0/3 | 0/1 |

In the primary cohort, eight tools had no **required** parameters, including the two tools with zero parameter properties. None were flagged. Playwright contributed tools with legitimate usage guidance, including instructions for using page snapshots and screenshots. This is an initial utility check across two independent server families, with limited coverage of truly zero-parameter tools.

Reproduce the ablation with `.venv/bin/python -m eval.train_l3 --description-only --device cpu --output var/l3-description-only`. Install the three pinned Node packages below under `var/l3-utility-servers`, and have the pinned Time and Git packages cached for Python 3.13. The diagnostic runner accepts a Node 22 executable via `--node`.

```sh
npm install --prefix var/l3-utility-servers --ignore-scripts --save-exact \
  @playwright/mcp@0.0.86 @modelcontextprotocol/server-filesystem@2.4.0 @modelcontextprotocol/server-memory@2.2.1
.venv/bin/python -m eval.check_l3 > var/l3/diagnostics.json
```
