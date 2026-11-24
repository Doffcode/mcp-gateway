# Results

All empirical results are preliminary. The three kinds of evidence in this chapter are functional behavior on fixtures, screening outcomes on metadata, and judged outcomes from model responses.

## L1 change detection and live enforcement

The local metadata-change fixture demonstrates that a clean tool can be pinned, then removed when metadata changes. A benign update remains withheld until explicit reapproval, after which it can be served again. An update also flagged by L2 triggers quarantine. The evidence is the stored hash, the metadata diff, the gateway event, and the changed listing. This test demonstrates detection after pinning. During the benchmark each listing had a fresh store, so L1 only established an initial fingerprint.

In the live Weather fixture, the upstream advertises two tools. The gateway removes `get_weather` because the description implies access inconsistent with the advertised schema and serves `get_forecast`. A deliberate direct request to the removed tool returns a gateway error and generates a `call_blocked` event, with no upstream call. Qwen3 can still request the approved `get_forecast`, and the fixture returns a sample forecast. This illustrates the enforcement path for one local listing. The tool response and the agent's wording are displayed separately because the agent can embellish a result.

## Paired enforcement and tool availability

| Condition | Judged successes / pairs | Micro ASR | 95% interval |
|---|---:|---:|---:|
| No defense | 59/300 | 19.7% | 15.3–24.3% |
| L1+L2 and decision ladder | 37/300 | 12.3% | 8.7–16.3% |
| Paired difference | 22 net / 300 | 7.3 pp | 3.3–11.3 pp |

: Qwen3 8B thinking-enabled paired replay. Percentage-point differences use unrounded counts. {#tbl-asr}

@tbl-asr records the main enforcement outcome. A direct recount of the local pair artifact finds 31 pairs with success only without the gateway, 9 with success only with it, 28 successful in both, and 232 successful in neither. The change varied by risk category. Credential leakage dropped from 7/16 to 2/16, while instruction tampering rose from 4/16 to 6/16 and service disruption from 7/54 to 8/54. The macro averages across ten represented categories were 21.7% without filtering and 10.6% with filtering. Small strata support descriptive comparisons.

| First-sight metadata measure | Result |
|---|---:|
| Poisoned tool removed, paired sample | 96/300 cases |
| Poisoned tool removed through quarantine, paired sample | 22/300 cases |
| Poisoned tool served and an authentic tool removed, paired sample | 73/300 cases |
| Poisoned tool removed, full held-out static replay | 157/498 cases (31.5%) |
| Authentic-only removals, held-out servers | 3/128 tools (2.3%) |
| Authentic-only removals, training servers | 21/225 tools (9.3%) |
| Authentic-only removals, all benchmark servers | 24/353 tools (6.8%) |
| Quarantined authentic-only listings | 1/45 servers |
| Authentic hard negatives with trigger terms removed | 22/161 tools (13.7%) |

: Static removal and collateral availability outcomes, including removal by quarantine. {#tbl-availability}

As @tbl-availability shows, pinning and screening do not imply zero disruption. In the authentic benchmark sweep, five direct flaggings in Commander's listing triggered quarantine and removed all 19 of its tools. The 73 paired cases in which authentic tools were removed while the poisoned tool remained accessible show another mechanism by which the prompt can change. The paired result estimates the effect of the complete policy on the model input.

**Discrepancy in the earlier summary.** The archived results attribute all 37 gateway-side successes to L2 misses. Cross-tabulating the saved responses with the admission records shows 28/37 while the poisoned tool was served and 9/37 marked successful when it was removed. Success measures recognizable behavior in a text response. It is not evidence that a removed tool was called through the proxy. The nine cases require focused adjudication for the final thesis. The headline counts and paired interval are retained as recorded.

Agreement with the published response labels was 378/425 (88.9%) over four classes. For Success, 101 were positive in both, 8 were positive only under the local judge, and 21 were positive only in MCPTox. This indicates undercounting relative to the benchmark labels on this check. The replay contains 39/600 condition records marked as token-limited, including eight reused records. Judge error and truncation can affect the estimated change as well as the condition-level rates.

## Processing overhead

L3 timing uses the lab workstation's central processing unit (CPU).

| Measurement | Samples | Median | 95th percentile |
|---|---:|---:|---:|
| L1+L2 and ladder, first sight | 2,250 listings | 1.10 ms | 8.24 ms |
| L1+L2 and ladder, already pinned | 2,250 listings | 0.71 ms | 5.72 ms |
| L3 CPU score, one tool | 20 repetitions | 0.72 ms | 0.77 ms |
| L3 CPU score, twelve tools | 20 repetitions | 3.48 ms | 3.62 ms |

: Local processing times. Each row excludes MCP transport and tool execution. {#tbl-latency}

@tbl-latency separates the enforcement path from advisory scoring. The baseline benchmark includes writes for first-sight pins. The L3 artifact loaded in about 25.4 ms in the recorded run. These timings are from the lab machine and do not describe end-to-end agent response time. L4 is on-demand and its illustrative latency is reported separately.

## Frozen L3 screening

| Candidate | Additional poisoned flags / 465 served | Additional authentic flags / 204 served |
|---|---:|---:|
| Word and character TF–IDF | 465/465 | 0/204 |
| Frozen E5 | 461/465 | 8/204 |
| E5 fine-tuned, one epoch | 465/465 | 0/204 |
| E5 fine-tuned, two epochs | 465/465 | 0/204 |
| Frozen E5 with sibling names | 444/465 | 10/204 |

: Pooled out-of-fold model selection on the training servers. {#tbl-model-selection}

@tbl-model-selection shows why the CPU baseline was selected. The fine-tuned candidates tied its incremental flag counts on the selection data, and TF–IDF requires a smaller inference pipeline. The frozen threshold is 0.5436877, rounded from the saved value. Testing at this threshold gave 497 true-positive flags and one false-positive flag and one missed poisoned example. The observed recall and flag precision were both 497/498 (99.8%), with different denominators in meaning.

| Screen | Poisoned flagged | Authentic flagged | Added poisoned flags | Added authentic flags |
|---|---:|---:|---:|---:|
| No reconstructed arguments | 492/498 | 8/128 | 341/341 | 8/125 |
| Name and description only | 493/498 | 12/128 | 337/341 | 12/125 |
| Frozen full metadata | 497/498 | 1/128 | 340/341 | 1/125 |

: Held-out L3 and retrospective diagnostics. Added flags are measured on tools the baseline would serve. {#tbl-l3}

@tbl-l3 distinguishes screening the full split from screening the remaining tools. The reconstructed schema is a strong class correlate. There were no reconstructed arguments in 492/498 poisoned cases and 8/128 authentic tools. Of those, the frozen model flagged 491/492 and 0/8, respectively. It flagged 6/6 poisoned and 1/120 authentic tools with reconstructed arguments. The baseline already removed all six schema-bearing poisoned tools, so the 340 additional poisoned flags all came from the argument-free subset. The count-based shortcut flags one more poisoned tool among those served, while the full model flags seven fewer authentic tools in this subset of served tools. The text-only ablation suggests that wording also contains strong cues.

Exact and normalized metadata comparisons in the training report found no held-out matching examples under the tested normalizations. Shared templates or missingness patterns can still span servers. The local Weather smoke test scored the same tool about 0.132 with clean metadata and 0.659 with altered metadata. The forecast tool remained around 0.114 in both listings. This is one illustrative metadata contrast. These findings motivate testing on unfamiliar data and cannot yield an estimate of incremental ASR reduction.

## External authentic utility

| Subset | Direct L2 flags | L1+L2 removals | Added L3 flags among served |
|---|---:|---:|---:|
| All tools | 15/334 | 56/334 | 2/278 |
| All affected families | 7/19 | 7/19 | 2/16 |
| Explicitly zero parameters | 1/14 | 2/14 | 2/12 |
| Optional arguments only | 0/39 | 7/39 | 0/32 |
| At least one required argument | 14/281 | 47/281 | 0/234 |

: External authentic-only utility, using frozen L3 and first-sight baseline replay. {#tbl-utility}

@tbl-utility summarizes the 19 complete listings among 26 pinned candidates. Three server quarantines account for 52 of the 56 baseline removals. The model flagged four tools overall, two of which had already been removed. The additional flags were Contentful's `get_initial_context` and Microsoft Clarity's `login` with scores of approximately 0.798 and 0.590. Both were zero-parameter tools. The overall incremental flag rate is approximately 0.7% on 278 baseline-served tools, while the zero-parameter rate is approximately 16.7% on 12 such tools. The smaller group is a warning signal with a limited sample. Seven attempted sources failed to provide complete listings under the collection conditions. Configurations that can advertise tools locally form a convenience sample.

The independent labeled detection requirement remained open in the recorded study. The candidate release had to be verifiable, have usable metadata-level labels and terms, and include at least 50 deduplicated positives with populated schemas across at least three groups. No reviewed release met those conditions. The authentic-only cohort measures observed flags and replay availability. It has no poisoned examples from which to estimate recall.

## L4 workflow examples

| Case | Context | Local structured verdict |
|---|---|---|
| Weather `get_weather` | Altered description. Removed by gateway and flagged by L3 | Flagged · description |
| Weather `get_forecast` | Served fixture tool. Below L3 threshold | Low risk · input schema |
| Contentful `get_initial_context` | Authentic zero-parameter tool. Additional L3 flag | Low risk · description |
| Microsoft Clarity `login` | Authentic zero-parameter tool. Additional L3 flag | Low risk · description |

: Four targeted illustrative examples reviewed by local Qwen3 8B. {#tbl-l4}

@tbl-l4 demonstrates the Lab review workflow and the use of evidence fields. The first weather walkthrough recorded roughly 1.29–1.65 seconds for the two review requests. A later walkthrough recorded about 7.09 seconds for its first request and 1.22 seconds for the second. These are individual observations. The two authentic cases were selected because of their L3 results, so they cannot estimate L4 precision. Accuracy, added detection on routed cases, and any change in attack success remain open.
