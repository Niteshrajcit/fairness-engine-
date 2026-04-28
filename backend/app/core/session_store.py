from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data" / "sessions"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_session(metadata: dict[str, Any]) -> str:
    session_id = str(uuid4())
    payload = {
        "id": session_id,
        "created_at": _now(),
        "updated_at": _now(),
        "status": "uploaded",
        "metadata": metadata,
        "analysis": {},
        "simulation": {},
        "strategies": {},
        "selected_strategy_result": {},
        "replay_logs": [],
        "pipeline_state": {"completed_steps": [], "last_step": "uploaded"},
        "dataset_path": "",
    }
    save_session(payload)
    return session_id


def _session_path(session_id: str) -> Path:
    return DATA_DIR / f"{session_id}.json"


def save_session(payload: dict[str, Any]) -> None:
    payload["updated_at"] = _now()
    _session_path(payload["id"]).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def get_session(session_id: str) -> dict[str, Any] | None:
    path = _session_path(session_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_sessions() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(DATA_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        item = json.loads(path.read_text(encoding="utf-8"))
        rows.append(
            {
                "id": item["id"],
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
                "status": item.get("status"),
                "dataset_name": item.get("metadata", {}).get("filename", "unknown"),
            }
        )
    return rows

