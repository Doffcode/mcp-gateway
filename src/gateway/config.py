"""Config: gateway.yaml (committed) overlaid by config.local.yaml (per machine, gitignored)."""

from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Config:
    k: int = 2
    pin_store: Path = ROOT / "var" / "pins.json"
    log_file: Path | None = ROOT / "var" / "gateway.log"
    taxonomy_dir: Path = ROOT / "taxonomy"


def load(path: Path | None = None) -> Config:
    raw: dict = {}
    for p in (Path(path) if path else ROOT / "gateway.yaml", ROOT / "config.local.yaml"):
        if p.exists():
            raw.update(yaml.safe_load(p.read_text()) or {})
    cfg = Config()
    if "k" in raw:
        cfg.k = int(raw["k"])
    for key in ("pin_store", "log_file", "taxonomy_dir"):
        if raw.get(key):
            p = Path(raw[key])
            setattr(cfg, key, p if p.is_absolute() else ROOT / p)
    return cfg
