from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.explain import build_bias_explanation
from app.core.model import train_logistic_model
from app.core.session_store import get_session, save_session
from app.core.state import STATE
from app.core.strategy import evaluate_strategies

router = APIRouter()


class StrategySelection(BaseModel):
    strategy_name: str


def _group_outcomes(sensitive_values: pd.Series, predictions: pd.Series) -> list[dict]:
    frame = pd.DataFrame({"group": sensitive_values.values, "pred": predictions.values})
    rows: list[dict] = []
    for group, chunk in frame.groupby("group"):
        rows.append(
            {
                "group": str(group),
                "positive_rate": round(float((chunk["pred"] == 1).mean()) * 100, 2),
            }
        )
    return rows


@router.post("/strategy/generate")
def generate_strategies() -> dict:
    if STATE.df is None or not STATE.analysis:
        raise HTTPException(status_code=400, detail="Run analysis first.")

    target_col = STATE.schema["target_col"]
    sensitive_col = STATE.analysis["sensitive_attribute"]

    ranked = evaluate_strategies(
        df=STATE.df,
        target_col=target_col,
        sensitive_col=sensitive_col,
        baseline_accuracy=STATE.analysis["accuracy"],
        baseline_di=STATE.analysis["disparate_impact"],
    )
    recommended = ranked[0] if ranked else None
    recommendation = None
    if recommended:
        recommendation = {
            "strategy": recommended["name"],
            "reason": "Best fairness-accuracy balance from evaluated options.",
            "tradeoff": (
                f"Expected DI {recommended['di']} with accuracy loss "
                f"{recommended['accuracy_loss']}."
            ),
        }
    STATE.strategies = ranked
    output = {"message": "Strategies generated", "strategies": ranked, "recommendation": recommendation}
    if STATE.active_session_id:
        session = get_session(STATE.active_session_id)
        if session:
            session["strategies"] = output
            session["status"] = "strategies_generated"
            save_session(session)
    return output


@router.post("/strategy/apply")
def apply_strategy(payload: StrategySelection) -> dict:
    if STATE.df is None or not STATE.analysis:
        raise HTTPException(status_code=400, detail="Run analysis first.")

    strategy_name = payload.strategy_name
    valid_names = {s["name"] for s in STATE.strategies}
    if valid_names and strategy_name not in valid_names:
        raise HTTPException(status_code=400, detail="Invalid strategy selected.")

    target_col = STATE.schema["target_col"]
    sensitive_col = STATE.analysis["sensitive_attribute"]

    drop_columns: list[str] = []
    sample_weights = None
    work_df = STATE.df
    if strategy_name == "Remove Sensitive Feature":
        drop_columns = [sensitive_col]
    elif strategy_name == "Reweight Samples":
        group_counts = STATE.df[sensitive_col].value_counts()
        sample_weights = STATE.df[sensitive_col].map(lambda g: 1.0 / group_counts[g]).values
    elif strategy_name == "Resample Dataset":
        group_counts = STATE.df[sensitive_col].value_counts()
        smallest_group = group_counts.idxmin()
        max_count = int(group_counts.max())
        minority = STATE.df[STATE.df[sensitive_col] == smallest_group]
        if len(minority) < max_count:
            boost = minority.sample(max_count - len(minority), replace=True, random_state=42)
            work_df = pd.concat([STATE.df, boost], ignore_index=True).sample(frac=1.0, random_state=42)

    result = train_logistic_model(
        work_df, target_col, drop_columns=drop_columns, sample_weights=sample_weights
    )
    baseline_model = train_logistic_model(STATE.df, target_col)
    before_groups = _group_outcomes(
        baseline_model.X_test[sensitive_col], pd.Series(baseline_model.y_pred)
    )
    if strategy_name.startswith("Threshold Adjustment"):
        threshold = 0.6
        if "(" in strategy_name and strategy_name.endswith(")"):
            try:
                threshold = float(strategy_name.split("(")[-1].replace(")", ""))
            except ValueError:
                threshold = 0.6
        adjusted_pred = (result.y_proba >= threshold).astype(int)
        result_accuracy = float((result.y_test.values == adjusted_pred).mean())
        after_groups = _group_outcomes(result.X_test[sensitive_col], pd.Series(adjusted_pred))
    else:
        result_accuracy = result.accuracy
        after_groups = _group_outcomes(result.X_test[sensitive_col], pd.Series(result.y_pred))

    strategy_di = next((s["di"] for s in STATE.strategies if s["name"] == strategy_name), STATE.analysis["disparate_impact"])
    explanation = build_bias_explanation(
        sensitive_col=sensitive_col,
        di=strategy_di,
        change_rate=STATE.simulations.get("change_rate", 0.0),
        before_accuracy=STATE.analysis["accuracy"],
        after_accuracy=result_accuracy,
    )

    output = {
        "message": "Strategy applied and model retrained",
        "selected_strategy": strategy_name,
        "new_accuracy": round(result_accuracy, 4),
        "new_disparate_impact": round(float(strategy_di), 4),
        "before_after_outcomes": {"before": before_groups, "after": after_groups},
        "top_feature_importance": result.coefficients[:10],
        "explanation": explanation,
    }
    if STATE.active_session_id:
        session = get_session(STATE.active_session_id)
        if session:
            session["selected_strategy_result"] = output
            session["status"] = "mitigated"
            save_session(session)
    return output
