# Appendix A — Reproducibility and extended results {.unnumbered}

## Evidence map

Repository locations below refer to the Review III workspace. Raw benchmark, model artifacts, and detailed external captures are local build inputs. The report can be built from the editable report directory using the thesis profile in Report Kit.

- **Gateway and local fixtures.** The core modules are under `src/gateway/`. The pin-change, mismatch, and proxy tests are `tests/test_demo1_rugpull.py`, `tests/test_demo2_mismatch.py`, and `tests/test_lab.py`.
- **Paired evaluation.** Use `data/split.json`, `eval/run_mcptox.py`, `eval/judge.py`, and `eval/report.py`. The summary is in `results/results.md` and the run in `var/eval/mcptox_heldout_n300_think-on.jsonl`.
- **Classifier and external cohort.** Use `eval/train_l3.py`, `results/l3_screening.md`, `var/l3/results.json`, and `var/l3/diagnostics.json`. The external source manifest is `eval/sources/l3_external.json`. Findings are in `results/l3_external_utility.md` and `var/l3-external-r1/results.json`.
- **Review and demo.** L4 examples are in `var/l4/`. Walkthroughs and implementation notes are in `REVIEW-III.md`, `DEMO.md`, and `PROGRESS.md`.

The introduction to the historical `results/results.md` predates L3 and L4. Its ASR applies to the earlier deterministic configuration. The Results chapter reconciles its residual-success description with the saved pair records.

## Extended category results

| Risk category             | Paired cases | No defense | Baseline | Static removed |
|---------------------------|-------------:|-----------:|---------:|---------------:|
| Code Injection | 5 | 1 | 0 | 6/9 |
| Credential Leakage | 16 | 7 | 2 | 23/26 |
| Data Tampering | 20 | 3 | 1 | 15/33 |
| Financial Loss | 25 | 3 | 0 | 6/41 |
| Information Manipulation | 69 | 13 | 9 | 13/114 |
| Infrastructure Damage | 36 | 5 | 2 | 31/59 |
| Instruction Tampering | 16 | 4 | 6 | 6/27 |
| Message Hijacking | 7 | 2 | 0 | 6/12 |
| Privacy Leakage | 52 | 14 | 9 | 30/87 |
| Service Disruption | 54 | 7 | 8 | 21/90 |
| All represented categories | 300 | 59 | 37 | 157/498 |

: Category-level counts. The three middle columns are from the paired sample. The last column is from the full held-out static sweep. {#tbl-category}

@tbl-category combines two different experiments with explicit denominators. The Other category contains four examples in training and none on held-out servers.

## How to show the system at the review

1. In Gateway Lab, connect only the local Weather fixture with the gateway in path. Show the upstream listing of two tools and the downstream listing of one. Point to where L2 explains the removal and where L3 shows the separate score and threshold.
2. Send a deliberate manual request to the removed `get_weather` tool. Show the rejection in the gateway log and the absence of an upstream call. This is a focused proxy enforcement check.
3. Send the prefilled five-day forecast prompt in Agent Chat. Show the call to `get_forecast` and its fixture response. Expand the Weather discovery row or a raw frame if asked. When Ollama is unavailable, use a manual forecast call for the allowed path.
4. If time permits, request L4 on the captured Weather metadata and explain its advisory verdict. Present the paired benchmark and external utility figures as separate evidence from the live demonstration.

For a question about L1, show the metadata-change fixture and its unified diff, then the reapproval path. For a question about why the benchmark leaves residual successes, show the outcome and removal counts and explain the distinction between judged text and an actual runtime effect.
