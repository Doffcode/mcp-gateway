"""L2 capability consistency. Deterministic: regex only, no LLM, no network, no randomness.

implied  = categories whose action AND target patterns co-occur in one sentence of the description
           (or in the tool name).
declared = categories whose schema_hints match a parameter name, parameter description or `format`.
A tool is flagged for every category in implied - declared.

Not exhaustive: deterministic and auditable; wording outside the taxonomy's vocabulary can evade it.
"""

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

from .canonical import tool_view

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_CAMEL = re.compile(r"(?<=[a-z])(?=[A-Z])")


def _words(text: str) -> str:
    """'read_file' / 'sendMail' / 'get-actor' -> 'read file' / 'send Mail' / 'get actor'."""
    return re.sub(r"[_\-]+", " ", _CAMEL.sub(" ", text))


@dataclass(frozen=True)
class Pattern:
    regex: re.Pattern
    source: str

    @property
    def text(self) -> str:
        return self.regex.pattern


@dataclass(frozen=True)
class Category:
    name: str
    actions: tuple[Pattern, ...]
    targets: tuple[Pattern, ...]
    schema_hints: tuple[Pattern, ...]


@dataclass(frozen=True)
class Flag:
    category: str
    action: str  # matched text
    target: str
    target_pattern: str
    target_source: str
    evidence: str  # the sentence where both matched
    params: tuple[str, ...]

    def __str__(self) -> str:
        params = ", ".join(self.params) if self.params else "none"
        return (f"description implies {self.category} (action '{self.action}', target '{self.target}') "
                f"but the input schema declares no {self.category} parameter (params: {params})")

    def as_dict(self) -> dict:
        d = asdict(self)
        d["params"] = list(self.params)
        d["reason"] = str(self)
        return d


def _search(patterns: tuple[Pattern, ...], text: str) -> tuple[Pattern, str] | None:
    alt = _words(text)
    for p in patterns:
        for t in (text, alt):
            m = p.regex.search(t)
            if m:
                return p, m.group(0)
    return None


class L2Analyzer:
    def __init__(self, categories: list[Category]):
        self.categories = categories

    @classmethod
    def from_dir(cls, path: Path) -> "L2Analyzer":
        cats = []
        for f in sorted(Path(path).glob("*.yaml")):
            raw = yaml.safe_load(f.read_text())

            def comp(key: str) -> tuple[Pattern, ...]:
                return tuple(Pattern(re.compile(p["re"], re.IGNORECASE), p["source"]) for p in raw.get(key, []))

            cats.append(Category(raw["category"], comp("actions"), comp("targets"), comp("schema_hints")))
        return cls(cats)

    def implied(self, tool: Any) -> dict[str, tuple[str, Pattern, str, str]]:
        v = tool_view(tool)
        units = [u for u in _SENT_SPLIT.split(v["description"]) if u.strip()] + [_words(v["name"])]
        out = {}
        for c in self.categories:
            for u in units:
                a = _search(c.actions, u)
                t = _search(c.targets, u) if a else None
                if a and t:
                    out[c.name] = (a[1], t[0], t[1], u.strip())
                    break
        return out

    def declared(self, tool: Any) -> set[str]:
        props = (tool_view(tool)["inputSchema"] or {}).get("properties") or {}
        fields = []
        for pname, spec in props.items():
            fields.append(pname)
            fields.append(_words(pname).lower())
            if isinstance(spec, dict):
                fields += [str(spec.get("description", "")), str(spec.get("format", ""))]
        out = set()
        for c in self.categories:
            if any(p.regex.search(f) for p in c.schema_hints for f in fields if f):
                out.add(c.name)
        return out

    def __call__(self, tool: Any) -> list[Flag]:
        imp = self.implied(tool)
        dec = self.declared(tool)
        params = tuple(((tool_view(tool)["inputSchema"] or {}).get("properties") or {}).keys())
        return [Flag(c, action, tp_text, tp.text, tp.source, ev[:240], params)
                for c, (action, tp, tp_text, ev) in sorted(imp.items()) if c not in dec]
