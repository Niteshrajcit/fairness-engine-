from __future__ import annotations

import numpy as np
import pandas as pd


def selection_rate_by_group(
    df: pd.DataFrame, sensitive_col: str, predictions: pd.Series
) -> dict[str, float]:
    rates: dict[str, float] = {}
    temp = df[[sensitive_col]].copy()
    temp["pred"] = predictions.values
    for group, chunk in temp.groupby(sensitive_col):
        rates[str(group)] = float((chunk["pred"] == 1).mean())
    return rates


def disparate_impact(selection_rates: dict[str, float]) -> float:
    if len(selection_rates) < 2:
        return 1.0
    values = [v for v in selection_rates.values() if v > 0]
    if len(values) < 2:
        return 0.0
    return float(min(values) / max(values))


def statistical_parity_difference(selection_rates: dict[str, float]) -> float:
    if len(selection_rates) < 2:
        return 0.0
    vals = list(selection_rates.values())
    return float(max(vals) - min(vals))


def bias_risk_level(di: float, spd: float) -> str:
    if di < 0.6 or spd > 0.3:
        return "high"
    if di < 0.8 or spd > 0.15:
        return "medium"
    return "low"


def detect_proxy_bias(
    df: pd.DataFrame, sensitive_col: str, ignore_cols: list[str] | None = None
) -> list[dict[str, float | str]]:
    """Find features strongly associated with a sensitive attribute."""
    ignore_cols = ignore_cols or []
    candidates: list[dict[str, float | str]] = []
    for col in df.columns:
        if col == sensitive_col or col in ignore_cols:
            continue
        if df[col].nunique(dropna=True) <= 1:
            continue

        if pd.api.types.is_numeric_dtype(df[col]):
            encoded_sensitive = pd.Categorical(df[sensitive_col]).codes
            score = float(abs(np.corrcoef(df[col].fillna(df[col].median()), encoded_sensitive)[0, 1]))
        else:
            ctab = pd.crosstab(df[col], df[sensitive_col], normalize="index")
            if ctab.empty:
                continue
            score = float(ctab.max(axis=1).mean())

        if np.isnan(score):
            continue
        if score >= 0.35:
            candidates.append({"feature": col, "association_score": round(score, 4)})

    candidates.sort(key=lambda x: float(x["association_score"]), reverse=True)
    return candidates[:5]


def unified_bias_risk_score(disparate_impact_value: float, change_rate: float) -> dict[str, float | str]:
    """Create a normalized 0-100 bias risk score from fairness + counterfactual signals."""
    di_component = max(0.0, min(1.0, 1.0 - disparate_impact_value))
    cf_component = max(0.0, min(1.0, change_rate))
    score = 100.0 * ((0.65 * di_component) + (0.35 * cf_component))
    if score < 30:
        level = "Low"
    elif score < 70:
        level = "Medium"
    else:
        level = "High"
    return {"score": round(score, 2), "level": level}
