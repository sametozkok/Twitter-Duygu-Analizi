"""Run-based persistence for analysis sessions.

Bir "run" = bir analiz akisi. Match anti olusur, replies/sentiment eklenir.
Her run tek bir JSON dosyasinda yasar (data/analysis_runs/run_<id>.json).
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _runs_dir() -> Path:
    path = _project_root() / "data" / "analysis_runs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _run_path(run_id: str) -> Path:
    if not re.fullmatch(r"[0-9A-Za-z_\-]+", run_id):
        raise ValueError("Gecersiz run_id.")
    return _runs_dir() / f"run_{run_id}.json"


def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _new_run_id() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def _read_run(run_id: str) -> dict | None:
    path = _run_path(run_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_run(run_id: str, payload: dict) -> Path:
    path = _run_path(run_id)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def create_run(channels: list[str], matched_groups: list[dict]) -> str:
    run_id = _new_run_id()
    total_replies = sum(int(g.get("total_reply_count", 0) or 0) for g in matched_groups)
    payload = {
        "run_id": run_id,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "channels": channels,
        "matched_groups": matched_groups,
        "total_groups": len(matched_groups),
        "total_replies": total_replies,
        "has_replies": total_replies > 0,
        "has_sentiment": False,
        "sentiment_compare": None,
    }
    _write_run(run_id, payload)
    return run_id


def update_run_replies(
    run_id: str,
    matched_groups_with_replies: list[dict],
    total_replies: int,
) -> bool:
    payload = _read_run(run_id)
    if payload is None:
        return False
    payload["matched_groups"] = matched_groups_with_replies
    payload["total_replies"] = total_replies
    payload["has_replies"] = total_replies > 0
    payload["updated_at"] = _now_iso()
    payload["has_sentiment"] = False
    payload["sentiment_compare"] = None
    _write_run(run_id, payload)
    return True


def update_run_sentiment(
    run_id: str,
    compared_groups: list[dict],
    algorithms: list[str],
) -> bool:
    payload = _read_run(run_id)
    if payload is None:
        return False
    payload["has_sentiment"] = True
    payload["sentiment_compare"] = {
        "algorithms": algorithms,
        "compared_groups": compared_groups,
    }
    payload["updated_at"] = _now_iso()
    _write_run(run_id, payload)
    return True


def list_runs() -> list[dict]:
    runs_dir = _runs_dir()
    summaries: list[dict] = []
    for path in runs_dir.glob("run_*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        summaries.append({
            "run_id": data.get("run_id", path.stem.removeprefix("run_")),
            "created_at": data.get("created_at", ""),
            "updated_at": data.get("updated_at", ""),
            "channels": data.get("channels", []),
            "total_groups": int(data.get("total_groups", 0) or 0),
            "total_replies": int(data.get("total_replies", 0) or 0),
            "has_replies": bool(data.get("has_replies", False)),
            "has_sentiment": bool(data.get("has_sentiment", False)),
        })
    summaries.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return summaries


def get_run(run_id: str) -> dict | None:
    return _read_run(run_id)


def delete_run(run_id: str) -> bool:
    path = _run_path(run_id)
    if not path.exists():
        return False
    path.unlink()
    return True
