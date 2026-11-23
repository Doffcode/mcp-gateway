# Review III laptop handoff

Review III is **25 November 2026**. Bring the guide review form, the rough thesis, a project demo, the Phase II scope, and a results-first deck. The announced format allows two methodology slides and three results slides. The presentation is 12 minutes with 3 minutes for Q&A.

## Get the project running

```sh
git clone --branch review-iii https://github.com/Doffcode/mcp-gateway.git mcp-gateway-review
cd mcp-gateway-review
```

If you have the private review assets archive, put it in the cloned folder, verify its supplied SHA-256 checksum, and extract it at the repo root. The supplied offline runtime targets Linux x86-64. When using the full offline bundle, enter its `mcp-gateway` directory instead of cloning.

Without the archive, use [uv](https://docs.astral.sh/uv/getting-started/installation/) to prepare the CPU demo:

```sh
./scripts/setup_review.sh
```

That path fetches the fixed MCPTox data and trains the same CPU recipe if no model is present. It gives the laptop a demo scorer. The private archive carries the exact frozen artifact, pairwise raw run, and external per-tool reports.

Start the dashboard and open `http://127.0.0.1:8765/lab`:

```sh
./scripts/review_demo.sh
```

In **Live Wire**, leave **Weather** and **Filesystem** selected, deselect the other servers, and keep the gateway **In the path**. Click **Connect**. The altered weather tool shows an L2 reason and an L3 flagged score of about **0.6592** against threshold **0.5436877**. The decision column attributes removal to the existing gateway. The forecast tool stays served. L3 runs on CPU and the walkthrough does not require Ollama. For the agent before/after replay, open Story mode, choose scene 2, and select **Recorded run**.

## Brief the guide

| Evidence | Claim to make |
|---|---|
| Existing paired MCPTox result | L1+L2 reduced observed attack success from **59/300 to 37/300** (19.7% to 12.3%, difference 7.3 percentage points, 95% CI 3.3–11.3). In this first-sight setup the detection came from L2 and the decision ladder. |
| L3 screening on frozen MCPTox | L3 flagged **340/341** poisoned examples and **1/125** authentic tools that the existing gateway would have served. It did not control admission and the run did not measure additional attack-success reduction. |
| External utility | Across **334 authentic tools from 19 unfamiliar families**, L2 flagged 15, the existing ladder removed 56, and L3 added **2/278** flags after baseline removals. Both were zero-parameter tools (**2/12** still served in that subset). |
| Phase II | Seek an eligible independent labeled metadata set, especially records with populated schemas. Measure the effect of L3 enforcement in a separate paired experiment before considering it for the default gateway. Test L4 only if a second review adds useful evidence. |

Read [benchmark evidence](results/results.md), [L3 results](results/l3_screening.md), and [external utility](results/l3_external_utility.md). A [repo handoff](PROGRESS.md) describes the latest implementation. The existing presentation files are from Review II. Review III slides, the rough thesis chapters, and the current guide form still need to be finalized.
