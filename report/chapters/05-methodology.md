# Experimental methodology

## Data and unit of analysis

The project pins the MCPTox source revision to `f85189f9`. Ingestion excludes 36 records marked as invalid from 1,348 source records and extracts 353 authentic tools. Parsed properties from the released text form reconstructed benchmark input schemas. Argument types are unavailable in the source, so the benchmark L2 analysis uses parameter names and descriptions. The frozen split uses seed 20261012 and groups cases by server. The train and held-out server lists are disjoint. @tbl-split distinguishes the full held-out cohort from the subset used for model-response replay.

| Cohort | Server families | Poisoned cases | Authentic tools |
|---|---:|---:|---:|
| MCPTox training | 29 | 814 | 225 |
| MCPTox held-out | 16 | 498 | 128 |
| MCPTox total after filtering | 45 | 1,312 | 353 |
| Paired response replay, subset of held-out | 16 | 300 | — |
| External authentic cohort | 19 | Not sampled | 334 |

: Evaluation cohorts. The response replay reuses part of the held-out cohort. {#tbl-split}

The static experiments compare tool definitions. For a poisoned case the gateway evaluates the case's poisoned tool alongside that server's authentic definitions. An authentic-only evaluation uses the complete authentic listing, since quarantine depends on other tools on the same server. The tools or listings and their outcome labels are the reporting units, depending on the question.

## Paired model response experiment

The experiment selects 300 of the 498 held-out cases by proportional stratification on the source risk category, using largest-remainder allocation and seeded within-category sampling. The local runner uses Qwen3 8B via Ollama with thinking enabled, temperature zero, a fixed seed, and a 16,384-token context. The same user query and the same benchmark prompt format are used for both conditions. In the gateway condition, the evaluator applies the production admission ladder to reconstructed metadata and removes the prompt blocks corresponding to tools the policy removed. Both conditions ask the model to emit a tool-call representation. The runner judges text responses offline. The benchmark does not execute the proposed calls.

If the prompt is byte-identical after filtering, the runner reuses the no-defense response. This occurred in 131 of 300 pair records. This removes a source of variability for identical inputs, and makes the comparison a single paired run under the implementation's reuse rule. The local MCP fixture separately validates that the policy also works through stdio.

The deterministic judge parses model output for tool calls. It distinguishes a direct call to the poisoned tool from a response matching the case's inferred adversarial objective. That objective is inferred from recognizable argument-value text or a targeted authentic tool. The four labels are Success, Direct Execution, Ignored, and None. Only Success counts in the reported attack success rate (ASR). The project checks agreement against the benchmark's stored Qwen3 8B thinking responses as an independent check of the local judging rules on held-out examples.

For each case $i$, let $d_i$ be the no-defense success indicator minus the gateway success indicator. The mean of $d_i$ gives the paired ASR reduction. The code resamples the 300 case differences with replacement 1,000 times and takes the empirical 2.5th and 97.5th percentiles. The individual condition intervals also use a case-level percentile bootstrap. The sampling unit is the case, so the interval describes variation under this procedure and does not account for between-model differences or server clustering.

## Learned screening and operating point

The model inputs are the tool name, description, and deterministic text serialization of the input schema. The baseline combines word unigrams and bigrams with character 3–5 grams and class-weighted logistic regression. Server identity, labels, and category names are excluded from the feature fields. The server identity is used for grouping, and labels are used as training targets and to score predictions. One experimental contextual encoder candidate also used sibling tool names. The deployed model uses only the target tool's fields.

Five stratified, server-grouped training folds produce out-of-fold scores. Threshold selection maximizes flags on poisoned tools missed by L2 and served by the baseline, subject to at most 5% additional flags on the 204 authentic training tools the baseline would serve. Ties favor fewer authentic flags, then the simpler candidate. The selected model is refit on all 29 training servers with the operating threshold carried forward. The main held-out evaluation applies only the selected model. The later no-arguments and name-and-description comparisons reuse the known held-out data and are interpreted as diagnostics.

## External utility and local demonstrations

The external source manifest froze candidate versions, runtime and dependency evidence, the L3 artifact, and taxonomy before scoring. Families already present in MCPTox and previously scored families were excluded from the primary cohort. Local stdio collection used namespace isolation, blocked network access, and collected complete listings without calling tools. Complete listings were fingerprinted and deduplicated at tool level. Per-family and per-tool results are reported. Some servers required startup placeholders, so metadata reflects the recorded configuration.

The external evaluation applies the frozen scorer and first-sight baseline replay. It measures direct L2 flags, actual replay removals, and L3 flags among tools that would remain available. The denominator for additional L3 flags is the baseline-served set. An explicit zero-parameter schema represents zero declared properties under the study's parser, distinct from optional-only arguments or missing schema information.

Owned local fixtures provide functional evidence for reapproval, removal, rejection before forwarding, and an allowed forecast response. L4 is demonstrated on two fixture tools and the two authentic examples additionally flagged by L3. These examples establish that the workflow returns an interpretable result on selected inputs. A representative L4 evaluation requires a separate labeled routed cohort.
