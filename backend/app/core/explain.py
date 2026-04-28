from __future__ import annotations

from typing import Any


def build_bias_explanation(
    sensitive_col: str,
    di: float,
    change_rate: float,
    before_accuracy: float,
    after_accuracy: float | None = None,
) -> dict[str, Any]:
    summary = (
        f"Bias was detected on '{sensitive_col}' with disparate impact {di:.3f}. "
        f"Counterfactual flips changed {change_rate:.1%} of decisions."
    )
    if after_accuracy is not None:
        summary += (
            f" Accuracy moved from {before_accuracy:.3f} to {after_accuracy:.3f} "
            "after strategy application."
        )

    return {
        "what_bias_existed": f"Disparate impact below fairness threshold on {sensitive_col}.",
        "why_it_happened": "Sensitive-group selection rates were imbalanced.",
        "what_changed": "The selected mitigation strategy rebalanced outcomes.",
        "final_improvement": summary,
    }
