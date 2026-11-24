# Review III laptop handoff

Review III is **25 November 2026**. Bring the guide review form, the rough thesis, a project demo, the Phase II scope, and a results-first deck. The announced format allows two methodology slides and three results slides. The presentation is 12 minutes with 3 minutes for Q&A.

## Get the project running

```sh
git clone --branch review-iii https://github.com/Doffcode/mcp-gateway.git mcp-gateway-review
cd mcp-gateway-review
```

If the laptop already has the project, use `git switch review-iii` and `git pull --ff-only origin review-iii` in that checkout.

Sign in as the repository owner and open the [laptop handoff draft](https://github.com/Doffcode/mcp-gateway/releases/tag/untagged-1c40124b9f8135a1b495). Download `review-assets-linux-x86_64.tar.gz` and `SHA256SUMS`. Copy them into the project directory, then verify and extract the Linux x86-64 bundle:

```sh
sha256sum -c SHA256SUMS
tar -xzf review-assets-linux-x86_64.tar.gz
```

The same draft has the built PowerPoint, slide preview, rough thesis PDF and Word copy, viva brief, and project checkpoint. The editable source is in the Git checkout. Keep the handoff unpublished. If using an earlier full offline bundle, run the Git update from its `mcp-gateway` directory.

Without the archive, use [uv](https://docs.astral.sh/uv/getting-started/installation/) to prepare the CPU demo:

```sh
./scripts/setup_review.sh
```

That path fetches the fixed MCPTox data and trains the same CPU recipe if no model is present. It gives the laptop a demo scorer. The private archive carries the exact frozen artifact, pairwise raw run, and external per-tool reports.

Start the dashboard and open `http://127.0.0.1:8765/lab`:

```sh
./scripts/review_demo.sh
```

In **Live Wire**, select only **Weather**, keep the gateway **In the path**, and click **Connect servers**. The connection path and listing show two tools offered and one available to the agent. Point to the L2 removal reason for `get_weather`, then to its advisory L3 score of about **0.6592** against threshold **0.5436877**. In **Test a tool call**, pick `get_weather` marked **Removed · test rejection**. The gateway log shows that the rejection happened before forwarding.

In **Agent Chat**, send the prefilled five-day forecast request. The chat shows the model's tool choice, and the wire trace shows the gateway forwarding `get_forecast` and Weather returning the local fixture's response. If Ollama is unavailable, use **Test a tool call** to request `get_forecast` directly. The screening and manual call paths run on CPU. For the agent before/after replay, open Story mode, choose scene 2, and select **Recorded run**.

For an optional live L4 walkthrough, make `qwen3:8b` available in Ollama on `127.0.0.1:11434`. In Lab click **Review with L4** on the weather tool and then on the forecast tool. L4 displays its verdict, evidence field, reason, and latency. **Suggested** marks disagreement between L2 and L3 or an L3 score within 0.05 of its threshold. The decision column continues to show the L1+L2 enforcement outcome. If local Ollama is unavailable, use the offline L3 walkthrough.

## Brief the guide

| Evidence | Claim to make |
|---|---|
| Existing paired MCPTox result | L1+L2 reduced observed attack success from **59/300 to 37/300** (19.7% to 12.3%, difference 7.3 percentage points, 95% CI 3.3–11.3). In this first-sight setup the detection came from L2 and the decision ladder. |
| L3 screening on frozen MCPTox | L3 flagged **340/341** poisoned examples and **1/125** authentic tools that the existing gateway would have served. It did not control admission and the run did not measure additional attack-success reduction. |
| External utility | Across **334 authentic tools from 19 unfamiliar families**, L2 flagged 15, the existing ladder removed 56, and L3 added **2/278** flags after baseline removals. Both were zero-parameter tools (**2/12** still served in that subset). |
| Phase II | Seek an eligible independent labeled metadata set, especially records with populated schemas. Measure the effect of L3 enforcement in a separate paired experiment before considering it for the default gateway. Evaluate L4 on the cases that would be routed to it and measure its incremental value. |

Read [benchmark evidence](results/results.md), [L3 results](results/l3_screening.md), and [external utility](results/l3_external_utility.md). A [repo handoff](PROGRESS.md) describes the latest implementation. The rough thesis and one-page viva brief are under `report/`. Report Kit builds the thesis PDF and Word document into `report/out/`. The editable Review III PowerPoint and PDF preview are in `slides/out/` under the name `review-iii`. The build source and timed notes are in `slides/review-iii/`. The current guide form is still open.
