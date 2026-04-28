from __future__ import annotations

import pandas as pd

SENSITIVE_KEYWORDS = ["gender", "sex", "race", "ethnicity", "age", "religion", "marital", "disability"]


def infer_schema(df: pd.DataFrame) -> dict:
    target_col = df.columns[-1]
    features = [col for col in df.columns if col != target_col]
    categorical = df[features].select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    numerical = [c for c in features if c not in categorical]
    sensitive = detect_sensitive_attributes(df, features)
    return {
        "target_col": target_col,
        "features": features,
        "categorical_features": categorical,
        "numerical_features": numerical,
        "sensitive_attributes": sensitive,
    }


def detect_sensitive_attributes(df: pd.DataFrame, features: list[str]) -> list[str]:
    sensitive_cols: list[str] = []
    for col in features:
        low_cardinality = df[col].nunique(dropna=True) <= max(8, int(len(df) * 0.05))
        keyword_match = any(k in col.lower() for k in SENSITIVE_KEYWORDS)
        if keyword_match or low_cardinality:
            sensitive_cols.append(col)
    return sensitive_cols
