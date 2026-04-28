from __future__ import annotations

from io import StringIO
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.session_store import DATA_DIR, create_session, get_session, save_session
from app.core.state import STATE
from app.utils.parser import infer_schema
from app.utils.preprocess import normalize_target

router = APIRouter()


@router.post("/upload")
async def upload_dataset(file: UploadFile = File(...)) -> dict:
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    raw = (await file.read()).decode("utf-8")
    df = pd.read_csv(StringIO(raw))
    if df.shape[1] < 2:
        raise HTTPException(status_code=400, detail="CSV must contain at least two columns.")

    schema = infer_schema(df)
    df = normalize_target(df, schema["target_col"])

    STATE.df = df
    STATE.schema = schema
    STATE.analysis = {}
    STATE.simulations = {}
    STATE.strategies = []
    STATE.replay_logs = []
    STATE.pipeline_step = "uploaded"
    STATE.cancel_requested = False

    session_id = create_session(
        {
            "filename": file.filename,
            "rows": len(df),
            "columns": df.columns.tolist(),
            "target_col": schema["target_col"],
            "sensitive_attributes": schema["sensitive_attributes"],
        }
    )
    csv_path = DATA_DIR / f"{session_id}.csv"
    csv_path.write_text(raw, encoding="utf-8")
    session = get_session(session_id)
    if session is not None:
        session["dataset_path"] = str(Path(csv_path))
        session["metadata"]["schema"] = schema
        save_session(session)
    STATE.active_session_id = session_id

    return {
        "message": "Dataset received",
        "session_id": session_id,
        "rows": len(df),
        "columns": df.columns.tolist(),
        "schema": schema,
    }
