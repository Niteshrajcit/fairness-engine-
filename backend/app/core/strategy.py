from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.core.bias import disparate_impact, selection_rate_by_group
from app.core.model import train_logistic_model


@dataclass
class StrategyResult:
    name: str
    accuracy: float
    di: float
    bias_reduction: float
    accuracy_loss: float


def _evaluate_strategy(
    name: str,
    df: pd.DataFrame,
    target_col: str,
    sensitive_col: str,
    baseline_accuracy: float,
    baseline_di: float,
    drop_columns: list[str] | None = None,
    sample_weights: np.ndarray | None = None,
) -> StrategyResult:
    artifacts = train_logistic_model(
        df=df, target_col=target_col, drop_columns=drop_columns, sample_weights=sample_weights
    )
    rates = selection_rate_by_group(artifacts.X_test, sensitive_col, pd.Series(artifacts.y_pred))
    di = disparate_impact(rates)
    return StrategyResult(
        name=name,
        accuracy=artifacts.accuracy,
        di=di,
        bias_reduction=max(0.0, di - baseline_di),
        accuracy_loss=max(0.0, baseline_accuracy - artifacts.accuracy),
    )


def evaluate_strategies(
    df: pd.DataFrame, target_col: str, sensitive_col: str, baseline_accuracy: float, baseline_di: float
) -> list[dict]:
    outputs: list[StrategyResult] = []

    if sensitive_col in df.columns:
        outputs.append(
            _evaluate_strategy(
                name="Remove Sensitive Feature",
                df=df,
                target_col=target_col,
                sensitive_col=sensitive_col,
                baseline_accuracy=baseline_accuracy,
                baseline_di=baseline_di,
                drop_columns=[sensitive_col],
            )
        )

    group_counts = df[sensitive_col].value_counts()
    if len(group_counts) > 1:
        inv_freq = df[sensitive_col].map(lambda g: 1.0 / group_counts[g]).values
        outputs.append(
            _evaluate_strategy(
                name="Reweight Samples",
                df=df,
                target_col=target_col,
                sensitive_col=sensitive_col,
                baseline_accuracy=baseline_accuracy,
                baseline_di=baseline_di,
                sample_weights=inv_freq,
            )
        )

        smallest_group = group_counts.idxmin()
        max_count = int(group_counts.max())
        minority = df[df[sensitive_col] == smallest_group]
        if len(minority) < max_count:
            boost = minority.sample(max_count - len(minority), replace=True, random_state=42)
            resampled = pd.concat([df, boost], ignore_index=True).sample(frac=1.0, random_state=42)
            outputs.append(
                _evaluate_strategy(
                    name="Resample Dataset",
                    df=resampled,
                    target_col=target_col,
                    sensitive_col=sensitive_col,
                    baseline_accuracy=baseline_accuracy,
                    baseline_di=baseline_di,
                )
            )

    threshold_model = train_logistic_model(df=df, target_col=target_col)
    for threshold in [0.55, 0.6]:
        threshold_pred = (threshold_model.y_proba >= threshold).astype(int)
        threshold_rates = selection_rate_by_group(
            threshold_model.X_test, sensitive_col, pd.Series(threshold_pred)
        )
        threshold_di = disparate_impact(threshold_rates)
        threshold_accuracy = float((threshold_model.y_test.values == threshold_pred).mean())
        outputs.append(
            StrategyResult(
                name=f"Threshold Adjustment ({threshold})",
                accuracy=threshold_accuracy,
                di=threshold_di,
                bias_reduction=max(0.0, threshold_di - baseline_di),
                accuracy_loss=max(0.0, baseline_accuracy - threshold_accuracy),
            )
        )

    ranked = sorted(outputs, key=lambda x: (abs(1.0 - x.di), x.accuracy_loss))
    return [
        {
            "name": item.name,
            "accuracy": round(item.accuracy, 4),
            "di": round(item.di, 4),
            "bias_reduction": round(item.bias_reduction, 4),
            "accuracy_loss": round(item.accuracy_loss, 4),
        }
        for item in ranked
    ]
