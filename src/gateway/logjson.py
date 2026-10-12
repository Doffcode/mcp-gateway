"""Structured JSON logs: one JSON object per line, to stderr and optionally a file."""

import json
import sys
from pathlib import Path
from typing import Any


class JsonLog:
    def __init__(self, path: Path | None = None, stream=sys.stderr):
        self.path = path
        self.stream = stream
        self.records: list[dict] = []  # kept in memory so tests and demos can inspect them

    def emit(self, event: str, **fields: Any) -> dict:
        rec = {"event": event, **fields}
        self.records.append(rec)
        line = json.dumps(rec, sort_keys=True, ensure_ascii=False)
        if self.stream is not None:
            print(line, file=self.stream, flush=True)
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "a") as f:
                f.write(line + "\n")
        return rec
