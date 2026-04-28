from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.core.session_store import DATA_DIR, get_session, list_sessions, save_session
from app.core.state import STATE

router = APIRouter()


class ResumePayload(BaseModel):
    session_id: str


def _load_df_from_session(session: dict[str, Any]) -> pd.DataFrame:
    dataset_path = session.get("dataset_path")
    if not dataset_path or not Path(dataset_path).exists():
        raise HTTPException(status_code=404, detail="Session dataset not found.")
    return pd.read_csv(dataset_path)


@router.get("/sessions")
def sessions_list() -> dict[str, Any]:
    return {"sessions": list_sessions()}


@router.get("/session/{session_id}")
def session_detail(session_id: str) -> dict[str, Any]:
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return session


@router.post("/session/resume")
def resume_session(payload: ResumePayload) -> dict[str, Any]:
    session = get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    STATE.df = _load_df_from_session(session)
    STATE.schema = session.get("metadata", {}).get("schema", {})
    STATE.analysis = session.get("analysis", {})
    STATE.simulations = session.get("simulation", {})
    STATE.strategies = session.get("strategies", {}).get("strategies", [])
    STATE.replay_logs = session.get("replay_logs", [])
    STATE.active_session_id = payload.session_id
    STATE.pipeline_step = session.get("pipeline_state", {}).get("last_step", "uploaded")
    STATE.cancel_requested = False
    return {"message": "Session resumed", "session_id": payload.session_id, "last_step": STATE.pipeline_step}


@router.get("/session/{session_id}/export/json")
def export_session_json(session_id: str) -> JSONResponse:
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return JSONResponse(content=session)


@router.get("/session/{session_id}/export/pdf")
def export_session_pdf(session_id: str) -> StreamingResponse:
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    before = session.get("selected_strategy_result", {}).get("before_after_outcomes", {}).get("before", [])
    after = session.get("selected_strategy_result", {}).get("before_after_outcomes", {}).get("after", [])
    chart_path = DATA_DIR / f"{session_id}_chart.png"
    if before and after:
        groups = [r["group"] for r in before]
        before_vals = [r["positive_rate"] for r in before]
        after_map = {r["group"]: r["positive_rate"] for r in after}
        after_vals = [after_map.get(g, 0) for g in groups]
        x = range(len(groups))
        plt.figure(figsize=(6, 3))
        plt.bar([i - 0.2 for i in x], before_vals, width=0.4, label="Before")
        plt.bar([i + 0.2 for i in x], after_vals, width=0.4, label="After")
        plt.xticks(list(x), groups)
        plt.ylabel("Positive %")
        plt.legend()
        plt.tight_layout()
        plt.savefig(chart_path)
        plt.close()

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    y = 760
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, "AI Fairness Audit Report")
    y -= 25
    pdf.setFont("Helvetica", 10)

    meta = session.get("metadata", {})
    pdf.drawString(50, y, f"Dataset: {meta.get('filename', 'unknown')}")
    y -= 15
    pdf.drawString(50, y, f"Rows: {meta.get('rows', '-')}, Columns: {len(meta.get('columns', []))}")
    y -= 20
    analysis = session.get("analysis", {})
    simulation = session.get("simulation", {})
    pdf.drawString(50, y, f"Disparate Impact: {analysis.get('disparate_impact', '-')}")
    y -= 15
    pdf.drawString(50, y, f"Risk Score: {simulation.get('bias_risk_score', '-')} ({simulation.get('bias_risk_level', '-')})")
    y -= 15
    pdf.drawString(50, y, f"Counterfactual Change Rate: {simulation.get('change_rate', '-')}")
    y -= 20
    recommendation = session.get("strategies", {}).get("recommendation", {})
    pdf.drawString(50, y, f"Recommended Strategy: {recommendation.get('strategy', '-')}")
    y -= 15
    pdf.drawString(50, y, f"Tradeoff: {recommendation.get('tradeoff', '-')}")
    y -= 15
    selected = session.get("selected_strategy_result", {})
    pdf.drawString(50, y, f"Selected Fix: {selected.get('selected_strategy', '-')}")
    y -= 20

    if chart_path.exists():
        pdf.drawImage(str(chart_path), 50, y - 180, width=500, height=180, preserveAspectRatio=True)

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf")
