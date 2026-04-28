from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class SessionState:
    df: pd.DataFrame | None = None
    schema: dict[str, Any] = field(default_factory=dict)
    analysis: dict[str, Any] = field(default_factory=dict)
    simulations: dict[str, Any] = field(default_factory=dict)
    strategies: list[dict[str, Any]] = field(default_factory=list)
    replay_logs: list[dict[str, Any]] = field(default_factory=list)
    active_session_id: str | None = None
    pipeline_step: str = "idle"
    cancel_requested: bool = False


STATE = SessionState()
