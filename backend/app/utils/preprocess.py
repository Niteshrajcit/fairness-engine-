from __future__ import annotations

import pandas as pd


def normalize_target(df: pd.DataFrame, target_col: str) -> pd.DataFrame:
    """Convert target into binary 0/1 if needed."""
    updated = df.copy()
    if updated[target_col].dtype == "object":
        unique = updated[target_col].dropna().unique().tolist()
        if len(unique) == 2:
            mapping = {unique[0]: 0, unique[1]: 1}
            updated[target_col] = updated[target_col].map(mapping)
    updated[target_col] = pd.to_numeric(updated[target_col], errors="coerce").fillna(0).astype(int)
    return updated
