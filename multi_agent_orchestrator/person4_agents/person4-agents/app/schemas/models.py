"""
Structured contracts for the multi-agent layer (Person 4).

Everything that crosses a module boundary is defined here. Teammates should
import from this file rather than reaching into agent internals.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------
# Enumerations
# --------------------------------------------------------------------------


class Signal(str, Enum):
    """Directional signal emitted by an individual agent."""

    BULLISH = "BULLISH"
    NEUTRAL = "NEUTRAL"
    BEARISH = "BEARISH"


class FinalSignal(str, Enum):
    """Directional signal emitted by the synthesis layer (5 bands)."""

    BULLISH = "BULLISH"
    MODERATELY_BULLISH = "MODERATELY_BULLISH"
    NEUTRAL = "NEUTRAL"
    MODERATELY_BEARISH = "MODERATELY_BEARISH"
    BEARISH = "BEARISH"


class AgentStatus(str, Enum):
    SUCCESS = "success"
    INSUFFICIENT_DATA = "insufficient_data"
    FAILED = "failed"


class DataQuality(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NONE = "NONE"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Recommendation(str, Enum):
    """Action ladder. Ordered by `ACTION_LADDER` below."""

    BUY = "BUY"
    ACCUMULATE = "ACCUMULATE"
    HOLD = "HOLD"
    REDUCE = "REDUCE"
    SELL = "SELL"


# Ordered from most bearish action to most bullish action.
ACTION_LADDER: list[Recommendation] = [
    Recommendation.SELL,
    Recommendation.REDUCE,
    Recommendation.HOLD,
    Recommendation.ACCUMULATE,
    Recommendation.BUY,
]

SIGNAL_VALUE: dict[Signal, int] = {
    Signal.BULLISH: 1,
    Signal.NEUTRAL: 0,
    Signal.BEARISH: -1,
}

QUALITY_FACTOR: dict[DataQuality, float] = {
    DataQuality.HIGH: 1.0,
    DataQuality.MEDIUM: 0.8,
    DataQuality.LOW: 0.55,
    DataQuality.NONE: 0.0,
}


# --------------------------------------------------------------------------
# Agent output contract
# --------------------------------------------------------------------------


class Evidence(BaseModel):
    """A single traceable citation. Never fabricated — always retrieved."""

    source: str
    section: str = ""
    text: str = ""
    score: Optional[float] = None

    model_config = ConfigDict(extra="allow")


class AgentOutput(BaseModel):
    """The contract every agent must satisfy, success or failure."""

    agent: str
    status: AgentStatus = AgentStatus.SUCCESS
    signal: Signal = Signal.NEUTRAL
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reasoning: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    data_quality: DataQuality = DataQuality.NONE
    latency_ms: int = 0
    errors: list[str] = Field(default_factory=list)

    @property
    def usable(self) -> bool:
        """Only successful agents carry directional weight in synthesis."""
        return self.status == AgentStatus.SUCCESS and self.data_quality != DataQuality.NONE


# --------------------------------------------------------------------------
# Risk contract
# --------------------------------------------------------------------------


class RiskAssessment(BaseModel):
    risk_level: RiskLevel = RiskLevel.MODERATE
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    risk_factors: list[str] = Field(default_factory=list)
    personalization: list[str] = Field(default_factory=list)
    # How many rungs down the action ladder the recommendation may be moved.
    max_bullish_action: Recommendation = Recommendation.BUY
    downgrade_steps: int = 0
    exposure_pct: float = 0.0
    concentration_score: float = 0.0


# --------------------------------------------------------------------------
# Reasoning trace
# --------------------------------------------------------------------------


class TraceEvent(BaseModel):
    """One renderable step of the reasoning chain.

    The frontend can render `stage` as a heading and `summary` as body text
    without knowing anything about agent internals. `detail` is optional
    structured extra for expandable views.
    """

    step: int
    stage: str
    summary: str
    detail: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=_utcnow)


# --------------------------------------------------------------------------
# Inputs (lenient — teammates own the producers, we only read)
# --------------------------------------------------------------------------


class UserProfile(BaseModel):
    user_id: str = "unknown"
    display_name: str = ""
    risk_tolerance: str = "moderate"  # conservative | moderate | aggressive
    investment_horizon: str = "medium"  # short | medium | long
    experience_level: str = "intermediate"
    max_position_pct: float = 15.0
    concentration_score: Optional[float] = None
    cash_pct: float = 0.0
    holdings: list[dict[str, Any]] = Field(default_factory=list)
    behavioral_flags: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")

    def exposure_to(self, symbol: str) -> float:
        """Percent of portfolio already held in `symbol`."""
        target = (symbol or "").strip().upper()
        total = 0.0
        for holding in self.holdings:
            if str(holding.get("symbol", "")).strip().upper() == target:
                try:
                    total += float(holding.get("weight_pct", 0.0) or 0.0)
                except (TypeError, ValueError):
                    continue
        return total


# --------------------------------------------------------------------------
# Final output contract
# --------------------------------------------------------------------------


class AnalysisResult(BaseModel):
    symbol: str
    final_signal: FinalSignal = FinalSignal.NEUTRAL
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    recommendation: Recommendation = Recommendation.HOLD
    reasoning: list[str] = Field(default_factory=list)
    agent_outputs: list[AgentOutput] = Field(default_factory=list)
    sources: list[Evidence] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    personalization: list[str] = Field(default_factory=list)
    data_quality: DataQuality = DataQuality.NONE
    failed_agents: list[str] = Field(default_factory=list)
    reasoning_trace: list[TraceEvent] = Field(default_factory=list)

    # Extras that are useful for the UI / metrics dashboard but not required.
    directional_score: float = 0.0
    risk_level: RiskLevel = RiskLevel.MODERATE
    user_id: str = "unknown"
    total_latency_ms: int = 0
    generated_at: str = Field(default_factory=_utcnow)

    def to_frontend_dict(self) -> dict[str, Any]:
        """JSON-safe dict with enums flattened to strings."""
        return self.model_dump(mode="json")
