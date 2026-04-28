from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.bias import unified_bias_risk_score
from app.core.session_store import get_session, save_session
from app.core.model import train_logistic_model
from app.core.simulation import counterfactual_change_rate, flip_sensitive_values
from app.core.state import STATE

router = APIRouter()


class WhatIfPayload(BaseModel):
    feature_updates: dict[str, str | int | float | bool]


@router.post("/simulate")
def simulate_counterfactual() -> dict:
    if STATE.df is None or not STATE.analysis:
        raise HTTPException(status_code=400, detail="Run analysis first.")

    target_col = STATE.schema["target_col"]
    sensitive_col = STATE.analysis["sensitive_attribute"]

    base = train_logistic_model(STATE.df, target_col)
    overall_changes: list[dict] = []
    for attr in STATE.schema.get("sensitive_attributes", [])[:3]:
        flipped_df = flip_sensitive_values(STATE.df, attr)
        flipped = train_logistic_model(flipped_df, target_col)
        change_rate = counterfactual_change_rate(pd.Series(base.y_pred), pd.Series(flipped.y_pred))
        overall_changes.append({"attribute": attr, "change_rate": round(change_rate, 4)})

    primary_change = next(
        (item["change_rate"] for item in overall_changes if item["attribute"] == sensitive_col),
        overall_changes[0]["change_rate"] if overall_changes else 0.0,
    )
    risk = unified_bias_risk_score(float(STATE.analysis.get("disparate_impact", 1.0)), float(primary_change))
    confirmed = primary_change > 0.05
    result = {
        "message": "Counterfactual simulation complete",
        "change_rate": round(primary_change, 4),
        "sensitive_counterfactuals": overall_changes,
        "bias_confirmed": confirmed,
        "bias_risk_score": risk["score"],
        "bias_risk_level": risk["level"],
        "bias_risk_explanation": (
            "Combined fairness risk score from disparate impact and counterfactual decision shifts."
        ),
    }
    STATE.simulations = result
    if STATE.active_session_id:
        session = get_session(STATE.active_session_id)
        if session:
            session["simulation"] = result
            session["status"] = "simulated"
            save_session(session)
    return result


@router.post("/simulate/what-if")
def simulate_what_if(payload: WhatIfPayload) -> dict:
    if STATE.df is None:
        raise HTTPException(status_code=400, detail="Upload dataset first.")
    target_col = STATE.schema["target_col"]
    model = train_logistic_model(STATE.df, target_col)
    sample = STATE.df.drop(columns=[target_col]).iloc[0].copy()
    for key, value in payload.feature_updates.items():
        if key in sample.index:
            sample[key] = value
    one_row = pd.DataFrame([sample])
    prediction = int(model.model.predict(one_row)[0])
    probability = float(model.model.predict_proba(one_row)[0][1])
    return {
        "message": "What-if simulation complete",
        "applied_features": payload.feature_updates,
        "predicted_outcome": prediction,
        "positive_probability": round(probability, 4),
    }
