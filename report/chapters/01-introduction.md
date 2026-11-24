# Introduction

An agent host can put the descriptions of available tools into a large language model (LLM) context so that it can decide which tool to use. This is necessary for tool use, but the description comes from software that the agent operator may neither control nor audit. A tool listing can therefore carry a directive unrelated to the user's task. If the host passes that listing straight to the model, the model has already seen the directive by the time the host can ask someone to approve a call.

This work inserts a gateway between the agent's Model Context Protocol (MCP) client and a server. It inspects the metadata first, exposes the tools that pass the current admission policy, and uses the same decision to check the names of tools invoked through the proxy. The setting is an agent with a genuine task and an untrusted tool listing. The useful outcome is to preserve access to legitimate tools while reducing the chance that untrusted tool metadata steers the agent.

## Research questions

The main question is: **What protection can an inline gateway provide by inspecting MCP tool metadata before an LLM agent sees it, and what are the trade-offs in tool availability, latency, and generalization?** Three questions guide the evaluation.

1. Can the gateway identify a change to a previously pinned tool and enforce the resulting admission decision through the MCP proxy?
2. How does deterministic filtering affect the observed success of metadata poisoning, which benign tools become unavailable, and how much processing time does it add?
3. How much would a learned screen add after deterministic filtering, and what further evidence is required before giving it or an LLM reviewer enforcement authority?

## Contributions

- An inline local MCP proxy with canonical metadata pinning (L1), capability-consistency checks (L2), and an auditable decision ladder. An integration test and an interactive Lab exercise demonstrate the proxy's behavior.
- A server-grouped paired replay that measures model behavior, accompanied by separate estimates of static tool removals and gateway overhead.
- A held-out evaluation of a frozen classifier (L3) based on term frequency (TF) and inverse document frequency (IDF), diagnostics for dataset shortcuts, an external authentic-tool utility assessment, and an optional local structured reviewer (L4).

The evaluation distinguishes flags, removals, and judged successes. Each measures a different outcome.
