from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.core.session_store import get_session, save_session
from app.core.state import STATE
from app.routes.analyze import analyze_dataset
from app.routes.simulate import simulate_counterfactual
from app.routes.strategy import generate_strategies

router = APIRouter()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_log(step: str, message: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    row = {"step": step, "message": message, "timestamp": _now_iso(), "data": data or {}}
    STATE.replay_logs.append(row)
    return row


def _event(event_name: str, payload: dict[str, Any]) -> str:
    return f"event: {event_name}\ndata: {json.dumps(payload)}\n\n"


def _persist_session_update(**kwargs: Any) -> None:
    session_id = STATE.active_session_id
    if not session_id:
        return
    session = get_session(session_id)
    if not session:
        return
    for key, value in kwargs.items():
        session[key] = value
    save_session(session)


def _load_session_if_needed(session_id: str | None) -> None:
    if not session_id:
        return
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if STATE.active_session_id != session_id:
        if not session.get("dataset_path"):
            raise HTTPException(status_code=404, detail="Session dataset missing.")
        STATE.df = pd.read_csv(session["dataset_path"])
        STATE.schema = session.get("metadata", {}).get("schema", {})
        STATE.analysis = session.get("analysis", {})
        STATE.simulations = session.get("simulation", {})
        STATE.strategies = session.get("strategies", {}).get("strategies", [])
        STATE.replay_logs = session.get("replay_logs", [])
    STATE.active_session_id = session_id


def _is_cancelled() -> bool:
    return STATE.cancel_requested


@router.get("/stream/pipeline")
async def stream_pipeline(
    session_id: str | None = Query(default=None),
    resume_from_last_step: bool = Query(default=False),
) -> StreamingResponse:
    _load_session_if_needed(session_id)
    if STATE.df is None:
        raise HTTPException(status_code=400, detail="Upload a dataset first.")

    async def event_generator() -> AsyncGenerator[str, None]:
        if not resume_from_last_step:
            STATE.replay_logs = []
            STATE.pipeline_step = "start"
        STATE.cancel_requested = False
        try:
            analysis = STATE.analysis
            simulation = STATE.simulations
            strategies = {"strategies": STATE.strategies}

            if STATE.pipeline_step in {"start", "uploaded"}:
                start = _append_log("start", "Pipeline started.")
                yield _event("step", start)
                STATE.pipeline_step = "training"
                _persist_session_update(
                    replay_logs=STATE.replay_logs,
                    pipeline_state={"last_step": STATE.pipeline_step},
                    status="running",
                )
                await asyncio.sleep(0.2)

            if _is_cancelled():
                yield _event("cancelled", {"message": "Pipeline cancelled", "last_step": STATE.pipeline_step})
                return

            if STATE.pipeline_step == "training":
                train = _append_log("training", "Training model...")
                yield _event("step", train)
                await asyncio.sleep(0.3)
                STATE.pipeline_step = "bias_detection"
                _persist_session_update(replay_logs=STATE.replay_logs, pipeline_state={"last_step": STATE.pipeline_step})

            if _is_cancelled():
                yield _event("cancelled", {"message": "Pipeline cancelled", "last_step": STATE.pipeline_step})
                return

            if STATE.pipeline_step == "bias_detection":
                detect = _append_log("bias_detection", "Detecting bias...")
                yield _event("step", detect)
                analysis = analyze_dataset()
                yield _event("analysis", analysis)
                STATE.pipeline_step = "simulation"
                _persist_session_update(
                    analysis=analysis,
                    replay_logs=STATE.replay_logs,
                    pipeline_state={"last_step": STATE.pipeline_step},
                )
                await asyncio.sleep(0.3)

            if _is_cancelled():
                yield _event("cancelled", {"message": "Pipeline cancelled", "last_step": STATE.pipeline_step})
                return

            if STATE.pipeline_step == "simulation":
                sim_log = _append_log("simulation", "Running counterfactual simulation...")
                yield _event("step", sim_log)
                simulation = simulate_counterfactual()
                yield _event("simulation", simulation)
                STATE.pipeline_step = "strategy"
                _persist_session_update(
                    simulation=simulation,
                    replay_logs=STATE.replay_logs,
                    pipeline_state={"last_step": STATE.pipeline_step},
                )
                await asyncio.sleep(0.3)

            if _is_cancelled():
                yield _event("cancelled", {"message": "Pipeline cancelled", "last_step": STATE.pipeline_step})
                return

            if STATE.pipeline_step == "strategy":
                strategy_log = _append_log("strategy", "Generating mitigation strategies...")
                yield _event("step", strategy_log)
                strategies = generate_strategies()
                yield _event("strategies", strategies)
                STATE.pipeline_step = "done"
                _persist_session_update(
                    strategies=strategies,
                    replay_logs=STATE.replay_logs,
                    pipeline_state={"last_step": STATE.pipeline_step},
                    status="completed",
                )

            done = _append_log("done", "Pipeline complete.")
            yield _event(
                "done",
                {
                    "session_id": STATE.active_session_id,
                    "message": "Streaming pipeline complete",
                    "analysis": analysis,
                    "simulation": simulation,
                    "strategies": strategies,
                    "replay_logs": STATE.replay_logs,
                    "done": done,
                },
            )
        except Exception as exc:  # noqa: BLE001
            error_row = _append_log("error", f"Pipeline failed: {exc}")
            _persist_session_update(replay_logs=STATE.replay_logs, status="failed")
            yield _event("error", {"detail": str(exc), "log": error_row})

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/replay")
def get_replay_logs() -> dict[str, Any]:
    return {"timeline": STATE.replay_logs}


@router.post("/stream/cancel")
def cancel_stream(session_id: str | None = Query(default=None)) -> dict[str, Any]:
    if session_id and STATE.active_session_id and session_id != STATE.active_session_id:
        raise HTTPException(status_code=400, detail="Can only cancel active session stream.")
    STATE.cancel_requested = True
    _persist_session_update(status="cancelled", pipeline_state={"last_step": STATE.pipeline_step})
    return {"message": "Cancellation requested", "session_id": STATE.active_session_id}
