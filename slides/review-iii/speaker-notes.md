# Review III speaker notes

## 1 · 0:35
Today I am presenting an MCP Metadata Integrity Gateway. MCP connects agents to external tools. The security question here is what happens before a tool is called, when an agent reads the server's description of what it can do. Our gateway checks that listing on the way to the agent. I will explain what the actual proxy enforces, what we measured in a paired experiment, and what the advisory stages add. The last minute shows the local tool path live.

## 2 · 1:00
Read the top row first. An upstream server returns a tool listing. The agent host may give its descriptions to the model to help it choose tools. A misleading description can influence that choice before any tool runs.

The second row uses the same listing and places a gateway in the discovery path. The inspected fields are the tool name, the free-text description, and the input schema, which describes the arguments. In the Weather example the description implies an unrelated capability that the city-only schema does not declare. The gateway can withhold that tool while preserving others.

Our objectives are to detect changes and capability mismatches, measure the change in judged attack success, and quantify authentic tool removal and latency. The security boundary here is metadata admission.

## 3 · 1:10
Follow the listing from the upstream MCP server through the proxy. L1 canonicalizes the three metadata fields and hashes them with SHA-256. On first sight it records a pin under the server and tool name. On later discoveries it compares against that pin and records a diff on change. The pin-change fixture shows a benign version withheld until explicit reapproval.

L2 compares capabilities implied by the name and description with those declared in the input schema. The ladder prioritizes quarantine. Two L2-flagged tools in a listing meet K equals two. A single tool with both an L1 mismatch and an L2 flag also triggers quarantine. Otherwise an isolated flag or a changed fingerprint removes the affected tool. The agent receives the filtered listing. If a client later names a removed tool, the proxy rejects that call before forwarding.

## 4 · 1:00
Separate the three experiments. First, the same 300 held-out MCPTox cases are compared with and without deterministic filtering at the same Qwen3 setting. These are responses to benchmark tool-list prompts.

Second, L3 chooses its model and threshold on five server-grouped folds over 29 training servers, with 814 poisoned examples and 225 authentic tools. We reserve 16 servers with 498 poisoned examples and 128 authentic tools. The objective rewards flags on L2 misses still served, under a five percent cap on extra authentic flags. Word and character TF–IDF with logistic regression ties the fine-tuned E5 candidates and wins on simpler inference.

Third, unfamiliar authentic listings measure availability and extra flags. Local examples show how the optional L4 workflow behaves. Admission comes from L1 and L2. Both learned layers report evidence.

## 5 · 1:45
This is the main enforcement result. With Qwen3 8B thinking enabled, 59 of 300 responses were judged successful without filtering and 37 of 300 with filtering. The paired difference is 7.3 percentage points, with a 95 percent case-bootstrap interval of 3.3 to 11.3. It comes from 31 cases that changed favorably and 9 that changed in the other direction. Both conditions use the same cases and query. The reported degree of precision uses the underlying counts, before rounding the rates.

This is a single replay over benchmark prompts. The rule-based judge checks the model's proposed calls or argument evidence, and the experiment does not execute those calls. L1 only sets its initial pin in this replay. The measured comparison reflects L2 and the ladder. Removing authentic tools can change the surrounding context too.

Put the cost beside the result: the baseline removed 3 of 128 authentic held-out tools. The p95 local processing overhead was 8.24 milliseconds on first sight and 5.72 when pinned, over 2,250 listings in each condition and excluding upstream transport.

Q&A · Why were there residual successes? Of 37, 28 occurred while the poisoned tool was still served and 9 were judged successful after the tool was removed. Those nine require adjudication and do not show a proxy bypass. The judge agreed with the source labels on 378/425 held-out responses and tended to undercount Success. Bootstrap inference is case-level and does not account for server clustering.

## 6 · 2:25
Read the two rows left to right. The held-out set contains 498 poisoned examples. Deterministic filtering would still serve 341. L3 flags 340 of those 341. The authentic row starts with 128 tools. The baseline would serve 125, and L3 flags one of them. A flag is a screening finding. This prototype continues to serve the tool if L1 and L2 allow it.

Now turn to the schema comparison. MCPTox presents its metadata as text, and we reconstruct arguments from that text. 492 of the 498 poisoned examples had no reconstructed arguments. Only 8 of 128 authentic tools did. There were six poisoned cases with reconstructed arguments, and the deterministic baseline removed all six. So all 340 additional poisoned flags are from the no-arguments group. A classifier can get a strong score from a corpus regularity that will not hold on every other source.

The diagnostic comparisons help quantify that concern. An empty-argument rule flags 341/341 poisoned and 8/125 authentic tools the baseline serves. The name-and-description-only model flags 337/341 and 12/125. Full metadata yields 340/341 and 1/125. Word choice carries signal, and the full model helps on authentic tools in this split. The diagnostic reuses the known holdout. It leaves performance on populated schemas from other sources open.

Q&A · Why keep L3 advisory if it flags 497/498 overall? The 497/498 result combines already-removed and served examples in a benchmark with strong schema imbalance. We need a fresh labeled cohort, especially populated schemas, then a paired agent study that actually turns on a defined L3 policy. No incremental attack-success reduction was measured here.

## 7 · 1:50
Now look at tools outside the benchmark. We collected complete listings for 334 authentic tools from 19 unfamiliar server families. The baseline removed 56, leaving 278. L3 flagged two among those 278. Both were in the 12 served tools with zero parameters. Three quarantines accounted for 52 of the 56 baseline removals. This is why a direct L2 flag count, which was 15, is different from the number of tools removed.

At the right is the optional local L4 review. On the Weather fixture it flagged the altered tool and rated the clean forecast low risk. It also rated the two externally flagged authentic examples low risk in a targeted check. These are four illustrative cases. The workflow can return a verdict with a field and reason. Accuracy needs a representative evaluation.

Q&A · What does the external study establish? It measures observed availability and additional flags for the authentic listings captured here. This is a convenience sample. It has no labeled poisoned examples and therefore cannot estimate independent detection recall. Zero parameters is a small subgroup with two flags, so the headline 2/278 alone is incomplete.

## 8 · 0:45
The next phase is designed around what each layer still needs. Reuse the measured deterministic gateway as the baseline. Test the frozen L3 scorer on independent labeled metadata with populated schemas, then compare an explicit L3 enforcement policy in a separate paired study. For L4, measure accuracy, latency and added value on cases that would actually reach the reviewer. I would also adjudicate the nine replay outcomes after removal before using the ASR estimate as the final thesis result.

Q&A · What would change the deployment decision? Evidence of recall on unfamiliar metadata, acceptable availability cost on authentic tools, and a reproducible paired gain in agent outcomes from the defined enforcement policy. For L4, check marginal value on routed cases alongside response time.

## 9 · 0:10
The specification defines the MCP tool interface. MCPTox supplies the benchmark. The repository records the implementation, experimental reports, and review walkthrough.

## 10 · 1:20
Thank you. Switch to the pre-opened Weather-only Lab. The gateway is in path. Show two tools offered and one served. Point to the L2 reason beside the removed get_weather tool. Select that tool in the manual call tester and show the gateway rejection before forwarding. In Agent Chat, send the prefilled forecast request and point to the get_forecast call and the fixture's response.

Fallback: if the model is unavailable, invoke the served forecast manually through the gateway. If switching windows would overrun, describe the two paths from the prepared Lab view and return here. Leave the final screen for the separate three-minute Q&A.
