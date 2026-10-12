# L2 capability taxonomy

Five categories, one YAML file each, with three pattern lists:

- `actions`: verbs (regex, case-insensitive, matched on the description and tool name)
- `targets`: nouns/paths/resources (same text)
- `schema_hints`: matched against parameter **names** and parameter **descriptions** (and JSON-schema `format`)

A category is **implied** when an action and a target match in the same sentence of the description (or in the
tool name). It is **declared** when any schema hint matches the input schema. A tool is flagged when
implied ⊄ declared.

Every pattern carries a `source`:
- `qsag-core@0.2.2`: PyPI qsag-core 0.2.2 `scanner.POISONING_PATTERNS` (Apache-2.0). 0.2.3 ships empty lists.
- `cisco-mcp-scanner@5d147dc/<file>`: github.com/cisco-ai-defense/mcp-scanner `mcpscanner/data/yara_rules/<file>.yara`
- `mcptox-train`: vocabulary observed in MCPTox **train-split** servers only (see data/split.json)
- `mcp-fixture-hygiene`: generic parameter names any honest tool of that category uses (schema side only)

Deterministic and auditable; wording outside this vocabulary can evade it.
