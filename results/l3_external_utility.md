# External L3 utility evaluation · 23 November 2026

The frozen TF–IDF classifier at threshold **0.5436877048965165** flagged **4/334 authentic tool definitions** from 19 MCP families outside the MCPTox and previous local cohorts. Two of those tools were already removed by L1+L2. L3 added **2/278 flags** among tools that would have remained available, affecting **2/16** families with at least one served tool. This was a screening and offline replay experiment. Admission policy stayed unchanged.

## Primary cohort

The [source manifest](../eval/sources/l3_external.json) fixed 26 pinned candidates, the Node and dependency lock hashes, the classifier and its manifest hashes, and the L2 taxonomy hashes before scoring. Collection used local stdio with Bubblewrap network isolation and no host home or credentials. It initialized each server and collected every tools/list page. No tools were called. Some versions require credential-shaped startup values, so their listings were collected with offline placeholders. The findings apply to the recorded configuration.

Nineteen distinct implementations returned complete listings. Seven did not return a complete listing in that environment: Cloudflare, Firebase, Neon, Railway, Supabase, Svelte, and Tableau. Families present in MCPTox, previously scored families, and close variants of those families were excluded from the primary cohort. The complete listings contained 334 distinct metadata fingerprints. Keeping complete listings took the run past the secondary 300-tool target. The cohort included **14 explicit zero-parameter tools across six families**, one tool below the target of 15.

Each metric is given as **tools affected / eligible tools · families affected / eligible families**. A family is eligible for additional flags when L1+L2 serves at least one tool in the corresponding subset.

| Metadata subset | Direct L2 flags | L1+L2 removals | Additional L3 flags after L1+L2 |
|---|---|---|---|
| **All authentic tools** | **15/334 · 7/19** | **56/334 · 7/19** | **2/278 · 2/16** |
| Explicitly zero declared parameters | 1/14 · 1/6 | 2/14 · 2/6 | **2/12 · 2/5** |
| Optional parameters only | 0/39 · 0/9 | 7/39 · 1/9 | 0/32 · 0/8 |
| One or more required parameters | 14/281 · 6/18 | 47/281 · 6/18 | 0/234 · 0/15 |
| Missing schema | 0/0 · 0/0 | 0/0 · 0/0 | 0/0 · 0/0 |
| Invalid or ambiguous schema | 0/0 · 0/0 | 0/0 · 0/0 | 0/0 · 0/0 |
| Description of at least 300 characters | 11/95 · 4/10 | 34/95 · 4/10 | 1/61 · 1/8 |
| Description mentions files or directories | 3/20 · 3/9 | 5/20 · 3/9 | 0/15 · 0/7 |
| Description mentions credentials or authentication | 3/7 · 3/5 | 6/7 · 4/5 | 0/1 · 0/1 |
| Description mentions networking or endpoints | 6/32 · 3/8 | 22/32 · 3/8 | 1/10 · 1/6 |

Description subsets overlap. The topic subsets use fixed text patterns. Zero-parameter means the schema explicitly lists no properties, or specifies an object with no properties and forbids additional ones. It is distinct from an optional-only or missing schema.

The first-sight replay used the existing L1+L2 ladder at K=2. Firecrawl, SAP Fiori, and Netlify were quarantined, accounting for 52 of the 56 removals. The two additional L3 flags were Contentful's `get_initial_context` (0.7978) and Microsoft Clarity's `login` (0.5904). Both had zero declared parameters. The overall rate therefore hides a higher observed flag rate in this small subset. The cohort is a convenience sample of publishers that can advertise tools locally. It does not establish a deployment-wide false-positive rate.

## Repeat check

Time and Playwright again yielded **0/27 flags across 0/2 families**. The three owned fixtures yielded **0/7** flags, and Git, Filesystem and Memory from MCPTox-associated families yielded **0/37**. These results are outside the primary cohort.

## Independent labeled detection

**Pending.** The release gate required a verifiable release and terms, labels on the metadata itself, and at least 50 deduplicated positive examples with populated schemas across three groups.

- MCP-AttackBench is described in the paper. A labeled, downloadable metadata release could not be verified from the official sources checked. [MCP-Guard paper](https://aclanthology.org/2026.findings-acl.240.pdf)
- The MCP rug-pull corpus provides before/after descriptions and authorization labels. Its record schema lacks tool input schemas. [Corpus schema](https://github.com/TANG-YB/mcp-rugpull-dataset#schema)
- The MCP-SafetyBench repository provides scenario material, but no explicit release license was found. No compatible licensed metadata subset was verified. [Author repository](https://github.com/xjzzzzzzzz/MCPSafety)

This evaluation establishes an external utility measurement. Independent recall and any incremental change in attack success remain unmeasured.

## Reproduction

The frozen capture, per-tool decisions, and repeat results are under `var/l3-external-r1/` (local, gitignored). The exact dependency lock is under `var/l3-external-packages/`. The capture SHA-256 is `6d9981205d0e68a86f7b8cc92b3ae106b2d26ee3ea8ca60e5859e35a55fa2cc5`.

To recapture, use the archived Node 22.16.0 binary and npm lock with the same installed package versions, and choose a fresh output directory:

```sh
.venv/bin/python -m eval.l3_external collect \
  --node var/l3-utility-runtime/node-v22.16.0-linux-x64/bin/node \
  --output var/l3-external-reproduction
.venv/bin/python -m eval.l3_external evaluate --output var/l3-external-reproduction
```
