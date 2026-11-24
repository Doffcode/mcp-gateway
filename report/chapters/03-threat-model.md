# Threat model and scope

## Trust boundary

The host discovers and invokes tools through the gateway. The policy files, local model artifacts, and pin store are trusted. The connected server and its metadata are untrusted. The operator configures server identity and controls reapproval. The design assumes the host uses the proxy and attackers cannot modify trusted state.

An adversary can influence metadata at first sight or change a previously encountered listing. The desired adversarial outcome is to influence a model to choose an unrelated action or misuse a legitimate tool. The checks are defined on metadata integrity and capability consistency rather than on the risk labels supplied by a benchmark. Coverage nonetheless depends on which fields are inspected, which capability signals are recognized, and what the scorer learned from its inputs.

## Scope of protection

The integrity check covers names, descriptions, and input schemas. A later change of the same named tool is detectable when the original pin is available and discovery runs again. A new tool name is a new pin-store key, and a first response is only a baseline for subsequent comparison. Server identity is configured locally. The metadata fingerprint has no publisher-signature semantics.

L2 compares descriptions with input schemas. An attacker may use wording outside the taxonomy or present an instruction that appears consistent with a declared parameter. A tool with a benign definition may still contain malicious code, return malicious content, or be called for an unauthorized purpose. Tool outputs, resource contents, call argument authorization, and direct user prompt misuse are outside this study's enforced policy.

The prototype runs locally over standard input/output (stdio). Production transport, shared state, and concurrent approval need further evaluation. Runtime resource limits belong to the host or sandbox.
