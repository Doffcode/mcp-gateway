from gateway.canonical import canonical_json, tool_hash


def test_key_order_and_whitespace_do_not_change_hash():
    a = {"name": "t", "description": "d", "inputSchema": {"type": "object", "properties": {"x": {"type": "string"}}}}
    b = {"inputSchema": {"properties": {"x": {"type": "string"}}, "type": "object"}, "description": "d", "name": "t"}
    assert canonical_json(a) == canonical_json(b)
    assert tool_hash(a) == tool_hash(b)


def test_only_pinned_fields_count():
    a = {"name": "t", "description": "d", "inputSchema": {}}
    b = {**a, "annotations": {"title": "x"}}
    assert tool_hash(a) == tool_hash(b)


def test_any_description_change_changes_hash():
    a = {"name": "t", "description": "d", "inputSchema": {}}
    assert tool_hash(a) != tool_hash({**a, "description": "d "})
