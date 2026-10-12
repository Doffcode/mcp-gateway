"""Canonical form of a tool's metadata and its SHA-256. Deterministic: no LLM, no network."""

import hashlib
import json
from typing import Any


def tool_view(tool: Any) -> dict:
    """The pinned fields only: {name, description, inputSchema}. Accepts an mcp Tool or a dict."""
    if not isinstance(tool, dict):
        tool = tool.model_dump(mode="json", by_alias=True, exclude_none=True)
    return {
        "name": tool.get("name", ""),
        "description": tool.get("description") or "",
        "inputSchema": tool.get("inputSchema") or {},
    }


def canonical_json(tool: Any) -> str:
    return json.dumps(tool_view(tool), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def tool_hash(tool: Any) -> str:
    return hashlib.sha256(canonical_json(tool).encode("utf-8")).hexdigest()


def pretty(tool: Any) -> str:
    """Stable multi-line rendering used for human-readable diffs."""
    return json.dumps(tool_view(tool), sort_keys=True, indent=2, ensure_ascii=False)
