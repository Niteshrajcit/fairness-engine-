from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, HTTPException

from app.core.bias import (
    bias_risk_level,
    detect_proxy_bias,
    disparate_impact,
    selection_rate_by_group,
    statistical_parity_difference,
)
from app.core.session_store import get_session, save_session
from app.core.model import train_logistic_model
from app.core.state import STATE

router = APIRouter()


@router.post("/analyze")
def analyze_dataset() -> dict:
    if STATE.df is None:
        raise HTTPException(status_code=400, detail="Upload a dataset first.")

    target_col = STATE.schema["target_col"]
    sensitive = STATE.schema["sensitive_attributes"]
    if not sensitive:
        raise HTTPException(status_code=400, detail="No sensitive attributes detected.")

    artifacts = train_logistic_model(STATE.df, target_col)
    sensitive_reports: list[dict] = []
    for sensitive_col in sensitive[:3]:
        rates = selection_rate_by_group(artifacts.X_test, sensitive_col, pd.Series(artifacts.y_pred))
        di = disparate_impact(rates)
        spd = statistical_parity_difference(rates)
        sensitive_reports.append(
            {
                "attribute": sensitive_col,
                "selection_rate": rates,
                "disparate_impact": round(di, 4),
                "statistical_parity_difference": round(spd, 4),
                "bias_detected": di < 0.8 or spd > 0.15,
                "risk": bias_risk_level(di, spd),
            }
        )

    sensitive_reports.sort(key=lambda x: (x["risk"], x["disparate_impact"]))
    primary = sensitive_reports[0]
    proxy_candidates = detect_proxy_bias(
        STATE.df,
        primary["attribute"],
        ignore_cols=[target_col],
    )
    intersectional = {}
    if len(sensitive) >= 2:
        intersection_cols = sensitive[:2]
        key_series = artifacts.X_test[intersection_cols].astype(str).agg(" | ".join, axis=1)
        intersection_df = pd.DataFrame({"intersection": key_series})
        rates = selection_rate_by_group(
            intersection_df, "intersection", pd.Series(artifacts.y_pred)
        )
        intersectional = {
            "attributes": intersection_cols,
            "selection_rate": rates,
            "disparate_impact": round(disparate_impact(rates), 4),
            "statistical_parity_difference": round(statistical_parity_difference(rates), 4),
        }

    result = {
        "message": "Bias analysis complete",
        "sensitive_attribute": primary["attribute"],
        "sensitive_audit": sensitive_reports,
        "accuracy": round(artifacts.accuracy, 4),
        "selection_rate": primary["selection_rate"],
        "disparate_impact": primary["disparate_impact"],
        "statistical_parity_difference": primary["statistical_parity_difference"],
        "bias_detected": primary["bias_detected"],
        "risk": primary["risk"],
        "proxy_bias_signals": proxy_candidates,
        "intersectional_bias": intersectional,
        "feature_importance": artifacts.coefficients,
        "shap": {"enabled": False, "note": "SHAP module can be plugged in later."},
    }
    STATE.analysis = result
    if STATE.active_session_id:
        session = get_session(STATE.active_session_id)
        if session:
            session["analysis"] = result
            session["status"] = "analyzed"
            save_session(session)
    return result
