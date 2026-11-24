# Gateway design and implementation

## Discovery and tool calls

The gateway is an MCP server upstream of the agent's tool client and an MCP client to the underlying server. @fig-gateway shows the enforcement path and the Lab's advisory path. The proxy requests the upstream listing, checks each definition, computes a decision for that server, and returns the approved entries. A subsequent call is checked against the most recent decision held by that proxy. If there is no decision yet, the proxy first generates one. A call to a removed or unknown tool, or to a quarantined server, returns an error at the proxy. Approved calls are forwarded and the upstream result is relayed. The implementation uses the last decision for calls, so the change-detection guarantee applies when a new listing is inspected.

![Inline MCP discovery and invocation. L1 and L2 feed the enforced decision; Gateway Lab receives captured metadata for advisory L3 and L4.](figures/gateway){#fig-gateway width=72%}

The proxy is implemented in `src/gateway/proxy.py`. The Lab taps both stdio hops to display real request and response frames. On a live listing, the Lab can show the upstream tool, the removal reason, the score and threshold, and the model review status. The live Agent Chat shows the tool call and actual tool response separately from the agent's natural-language answer. The chat trace displays calls first and groups discovery by server with expandable frames.

## L1 — Metadata fingerprint and reapproval

`src/gateway/canonical.py` extracts a fixed view of the name, description, and input schema. It serializes that view as compact, sorted-key JavaScript Object Notation (JSON) in Unicode Transformation Format (UTF-8) and computes a 256-bit Secure Hash Algorithm (SHA-256) digest. Stable serialization prevents object key ordering or incidental serialization whitespace from driving a mismatch. Changes to description content or ordered arrays can still change the hash. Empty descriptions and missing schemas are normalized by the canonical view where the input allows them.

`src/gateway/l1_pins.py` stores the canonical metadata and hash under the configured server/tool key. Under trust on first use (TOFU), the first observed value becomes the reference. A later mismatch produces a structured event and a unified diff. The old pin remains active, and the observed value is recorded as pending. An explicit command-line interface (CLI) approval replaces the pin with the pending value. This operation acknowledges a specific metadata change. Screening a whole listing for suspicious wording remains the gateway's responsibility.

## L2 — Capability consistency

`src/gateway/l2_capability.py` identifies capabilities implied by action and target patterns in the tool name and description, then compares them with capabilities supported by parameter names, types, and descriptions in the input schema. The taxonomy covers filesystem, network, credentials, subprocesses, and email. If an implied category is absent from the declared categories, L2 records a mismatch with the matched evidence. Taxonomy patterns are stored in `taxonomy/`, with source attributions supported by the fixture and logs.

Capability consistency is a heuristic. A legitimate tool can use defaults or a fixed resource without exposing an argument that matches the vocabulary. Conversely, a populated schema can agree with the tool's stated purpose while the metadata still contains a misleading instruction.

## Enforced decision ladder

In @tbl-ladder, the first two rows take priority over the tool-level outcomes. The threshold counts distinct tools with an L2 flag within the listing. Quarantine affects the availability of the whole server.

| Condition | Enforced action |
|---|---|
| Same tool has an L1 mismatch and an L2 flag | Quarantine the server |
| At least two tools are flagged by L2, with $K=2$ | Quarantine the server |
| An L2 flag below the quarantine threshold | Remove the flagged tool |
| L1 mismatch without an L2 flag | Remove the changed tool pending reapproval |
| Neither check requires removal | Serve the tool |

: Gateway admission rules implemented in `src/gateway/ladder.py`. {#tbl-ladder}

## L3 and L4 — Advisory inspection

The frozen L3 scorer converts the tool name, description, and reconstructed or advertised schema into text features. The live Lab passes the captured metadata to the scorer and displays the score, operating threshold, and verdict. The scorer uses a trusted local artifact and can report unavailable. The decisions enforced by the proxy come from L1 and L2.

For L4, an operator can ask the Lab to review one captured tool. The local Ollama model, Qwen3 8B, receives bounded metadata, sibling names, and the earlier screening signals. The Lab suggests review when L2 and L3 disagree or the L3 score lies within 0.05 of its threshold. It runs when requested. The reviewer has no tool access and returns a schema-validated verdict, evidence field, reason, and elapsed time. On transport or validation failure, the Lab can show unavailable. The structured output constrains the response format. Its substantive judgment still needs evaluation.
