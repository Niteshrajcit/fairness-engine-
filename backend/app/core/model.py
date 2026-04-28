from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


@dataclass
class ModelArtifacts:
    model: Pipeline
    X_test: pd.DataFrame
    y_test: pd.Series
    y_pred: np.ndarray
    y_proba: np.ndarray
    accuracy: float
    feature_names: list[str]
    coefficients: list[dict[str, float]]


def train_logistic_model(
    df: pd.DataFrame,
    target_col: str,
    drop_columns: list[str] | None = None,
    sample_weights: np.ndarray | None = None,
) -> ModelArtifacts:
    drop_columns = drop_columns or []
    X = df.drop(columns=[target_col] + drop_columns, errors="ignore")
    y = df[target_col]

    cat_cols = X.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    num_cols = [c for c in X.columns if c not in cat_cols]

    numeric_pipe = Pipeline(
        steps=[("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]
    )
    categorical_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[("num", numeric_pipe, num_cols), ("cat", categorical_pipe, cat_cols)]
    )

    model = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", LogisticRegression(max_iter=500, random_state=42)),
        ]
    )

    indices = np.arange(len(X))
    X_train, X_test, y_train, y_test, idx_train, _ = train_test_split(
        X,
        y,
        indices,
        test_size=0.2,
        random_state=42,
        stratify=y if y.nunique() > 1 else None,
    )

    fit_kwargs: dict[str, Any] = {}
    if sample_weights is not None:
        fit_kwargs["classifier__sample_weight"] = sample_weights[idx_train]

    model.fit(X_train, y_train, **fit_kwargs)
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    accuracy = float(accuracy_score(y_test, y_pred))

    feature_names = (
        model.named_steps["preprocessor"].get_feature_names_out().tolist()  # type: ignore[arg-type]
    )
    coefs = model.named_steps["classifier"].coef_[0]
    ranked = sorted(
        [{"feature": f, "importance": float(abs(c)), "signed": float(c)} for f, c in zip(feature_names, coefs)],
        key=lambda x: x["importance"],
        reverse=True,
    )

    return ModelArtifacts(
        model=model,
        X_test=X_test,
        y_test=y_test,
        y_pred=y_pred,
        y_proba=y_proba,
        accuracy=accuracy,
        feature_names=feature_names,
        coefficients=ranked[:20],
    )
