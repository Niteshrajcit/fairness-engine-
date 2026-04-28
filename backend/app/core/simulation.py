from __future__ import annotations

import pandas as pd


def flip_sensitive_values(df: pd.DataFrame, sensitive_col: str) -> pd.DataFrame:
    updated = df.copy()
    unique_values = list(updated[sensitive_col].dropna().unique())
    if len(unique_values) < 2:
        return updated
    first, second = unique_values[0], unique_values[1]
    updated[sensitive_col] = updated[sensitive_col].map(
        lambda x: second if x == first else first if x == second else x
    )
    return updated


def counterfactual_change_rate(original_pred: pd.Series, flipped_pred: pd.Series) -> float:
    if len(original_pred) == 0:
        return 0.0
    return float((original_pred != flipped_pred).mean())
