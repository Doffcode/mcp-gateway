# Discussion, validity, and Phase II

## Interpreting the evidence

The functional tests answer whether a controlled gateway can recognize metadata drift and enforce an admission decision. The benchmark answers what happened to judged model responses when the policy removed blocks from the presented tool list. The external study answers how often the same software would disrupt or flag authentic listings in a different sample. When these findings are combined, they support a narrow protection claim at the metadata boundary with a measurable availability cost.

The paired reduction is a net effect. The distribution of changes includes both favorable and unfavorable cases. It combines removal of suspicious metadata, changes in surrounding legitimate tool context, and ordinary model behavior under the two inputs. L1 contributes evidence in the longitudinal fixture. The fixed first-sight benchmark has no earlier trusted metadata against which to compare.

A tool's observed score should be interpreted with the baseline eligibility set and corpus construction. In MCPTox, L3 retained high recall and reduced false flags relative to a simple empty-schema heuristic over the full split. But all additional poisoned flags came from examples with no reconstructed arguments. In the external cohort both additional flags landed on a small subset of legitimate tools with explicitly empty parameter lists. These two facts make broad recall and production availability claims premature. Keeping L3 advisory lets the prototype collect evidence without turning those flags into denials.

## Threats to validity

- **Construct validity.** The response judge observes textual evidence, not successful side effects. It can miss a compliant response or mark one when the modeled behavior is implausible in the live environment. The nine apparent successes after removal need case-level review. The live fixture verifies actual proxy routing under controlled conditions.
- **Internal validity.** The comparison uses fixed model settings and a shared query. Tool removal sometimes also changes the surrounding authentic list. The reuse of identical prompts reduces noise but is a deliberate assumption about same-input behavior. Threshold selection operated on training folds. Diagnostic ablations reused known held-out results.
- **Statistical validity.** The paired bootstrap uses cases as the unit. Cases from a server may be correlated. Category counts can be small, and only one local model setting was evaluated in the main paired run. The interval is conditional on the case-level procedure and does not measure uncertainty across model families, runs, and servers.
- **External validity.** The benchmark contains strong schema and wording regularities. External tools were collected from publishers with locally runnable pinned packages, with incomplete listings excluded. Authentic-only data supports a utility assessment within that cohort. The selected L4 examples do not establish how a routing policy would behave on a representative workload.
- **Operational validity.** The prototype detects metadata mutation at discovery and checks call names against the latest decision. A production proxy would need explicit freshness semantics, trusted identity and state, appropriate resource authorization, and evaluation of the transport and failure policies. Tool metadata alone cannot attest to server behavior.

## Phase II evaluation plan

| Priority | Evidence to collect | Decision it supports |
|---|---|---|
| Adjudicate disagreement in the recorded paired runs | Inspect the nine successes after removal and a stratified set of judge agreements and disagreements. Report adjudication criteria, original labels, and reviewed labels | Clarify what the preliminary ASR includes |
| Evaluate a fresh labeled metadata cohort | Verify release terms and metadata labels, deduplicate by source and definition, stratify by family and schema completeness, and report recall among direct L2 misses | Decide whether L3 generalizes beyond MCPTox |
| Expand authentic utility measurement | Collect more zero-parameter and optional-only definitions, repeat by family, and compare adjacent pinned versions | Quantify tool flags, quarantines, and legitimate reapproval burden |
| Compare enforcement conditions on paired agent tasks | Freeze an eligible L3 decision policy before testing. Compare the baseline with that policy using judged outcomes and benign task completion | Determine whether L3 yields incremental protection at acceptable availability cost |
| Validate selective L4 review | Label a representative routed cohort and a comparison sample, record review errors and latency, and assess additional evidence over L2 and L3 | Determine where an LLM second opinion is worth its cost |

Protecting tool outputs, extending coverage to instructions outside MCP, and enforcing per-argument runtime authorization are separate research directions. Each has a different injection point or security objective. They can complement a metadata gateway once the current admission claim has been validated on fresh data.
