"""Local JSON persistence for analysis snapshots."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _analysis_dir() -> Path:
    path = _project_root() / "data" / "analysis_runs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_snapshot(prefix: str, payload: dict) -> str:
    analysis_dir = _analysis_dir()
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    file_name = f"{prefix}_{stamp}.json"
    file_path = analysis_dir / file_name

    with file_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)

    latest_path = analysis_dir / f"{prefix}_latest.json"
    with latest_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)

    return str(file_path.relative_to(_project_root()))
