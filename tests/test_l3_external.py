from eval.l3_external import schema_group, score_listing, summarize


class AlwaysFlags:
    def score_listing(self, tools):
        return [{"verdict": "flagged"} for _ in tools]


def tool(name, schema):
    return {"name": name, "description": "Example", "inputSchema": schema}


def test_schema_groups_distinguish_declared_parameters_and_missing_input():
    empty = {"type": "object", "properties": {}}
    props = {"type": "object", "properties": {"a": {"type": "string"}}}
    assert schema_group(tool("a", None)) == "missing"
    assert schema_group(tool("a", {})) == "invalid_or_ambiguous"
    assert schema_group(tool("a", {"type": "object"})) == "invalid_or_ambiguous"
    assert schema_group(tool("a", empty)) == "zero_parameters"
    assert schema_group(tool("a", props)) == "optional_only"
    assert schema_group(tool("a", {**props, "required": ["a"]})) == "required"
    assert schema_group(tool("a", {**props, "required": ["b"]})) == "invalid_or_ambiguous"


def test_utility_keeps_family_denominators_when_tools_are_deduplicated():
    schema = {"type": "object", "properties": {}}
    listing = [tool("clock", schema)]
    one = score_listing("one", listing, lambda _: [], AlwaysFlags(), 2)
    two = score_listing("two", listing, lambda _: [], AlwaysFlags(), 2)
    result = summarize(one + two)
    assert result["additional_l3"] == {
        "tools": 1, "tool_denominator": 1, "families": 2, "family_denominator": 2,
    }


def test_invalid_metadata_does_not_enter_complete_listing_replay():
    listing = [tool("clock", {"type": "object", "properties": {}}), tool("other", None)]
    rows = score_listing("one", listing, lambda _: [], AlwaysFlags(), 2)
    summary = summarize(rows)
    assert summary["direct_l2"]["tool_denominator"] == 1
    assert summary["baseline_removed"]["tool_denominator"] == 0
    assert summary["additional_l3"]["family_denominator"] == 0
