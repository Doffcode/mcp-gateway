"""L1 provenance pinning: TOFU pin store keyed by server/tool. Any hash change is a mismatch.

Deterministic: no LLM, no network, no randomness. Re-approval only via `gateway pin approve`.
"""

import difflib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .canonical import canonical_json, pretty, tool_hash


@dataclass(frozen=True)
class L1Result:
    status: str  # "new" (pinned now) | "match" | "mismatch"
    old_hash: str | None
    new_hash: str
    diff: str = ""


class PinStore:
    """JSON file: {"pins": {"server/tool": {...}}, "pending": {"server/tool": {...}}}."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.data = {"pins": {}, "pending": {}}
        if self.path.exists():
            self.data = json.loads(self.path.read_text())
            self.data.setdefault("pending", {})

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, sort_keys=True, indent=2, ensure_ascii=False))
        tmp.replace(self.path)

    @staticmethod
    def key(server: str, tool: str) -> str:
        return f"{server}/{tool}"

    def check(self, server: str, tool: Any) -> L1Result:
        canon = canonical_json(tool)
        h = tool_hash(tool)
        k = self.key(server, json.loads(canon)["name"])
        pin = self.data["pins"].get(k)
        if pin is None:
            self.data["pins"][k] = {"hash": h, "canonical": canon}
            self._save()
            return L1Result("new", None, h)
        if pin["hash"] == h:
            return L1Result("match", h, h)
        old = pretty(json.loads(pin["canonical"])).splitlines(keepends=True)
        new = pretty(tool).splitlines(keepends=True)
        diff = "".join(difflib.unified_diff(old, new, fromfile=f"{k} (pinned)", tofile=f"{k} (served)"))
        # Remember what was served so an operator can approve it explicitly; the pin is unchanged.
        self.data["pending"][k] = {"hash": h, "canonical": canon}
        self._save()
        return L1Result("mismatch", pin["hash"], h, diff)

    def approve(self, server: str, tool_name: str) -> str:
        k = self.key(server, tool_name)
        pending = self.data["pending"].pop(k, None)
        if pending is None:
            raise KeyError(f"no pending change for {k}")
        self.data["pins"][k] = pending
        self._save()
        return pending["hash"]

    def list(self) -> dict:
        return self.data
