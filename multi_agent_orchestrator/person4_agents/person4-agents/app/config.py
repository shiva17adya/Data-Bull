"""
Central configuration for the Person 4 agent module.

Everything tunable lives here so the demo can be adjusted without touching
agent logic. Values can be overridden with environment variables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

try:  # optional convenience, not a hard dependency
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover
    pass


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    # ---- LLM -------------------------------------------------------------
    # The module is fully functional with USE_LLM=false: every agent has a
    # deterministic reasoning path. The LLM enriches narrative reasoning and
    # may override the signal, but is never required.
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    anthropic_model: str = field(
        default_factory=lambda: os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
    )
    use_llm: bool = field(default_factory=lambda: _env_bool("USE_LLM", False))
    llm_max_tokens: int = field(default_factory=lambda: _env_int("LLM_MAX_TOKENS", 900))
    llm_timeout_s: float = field(default_factory=lambda: _env_float("LLM_TIMEOUT_S", 20.0))

    # ---- Orchestration ---------------------------------------------------
    agent_timeout_s: float = field(default_factory=lambda: _env_float("AGENT_TIMEOUT_S", 25.0))

    # ---- Synthesis weights ----------------------------------------------
    weight_technical: float = field(default_factory=lambda: _env_float("WEIGHT_TECHNICAL", 0.35))
    weight_fundamental: float = field(default_factory=lambda: _env_float("WEIGHT_FUNDAMENTAL", 0.40))
    weight_sentiment: float = field(default_factory=lambda: _env_float("WEIGHT_SENTIMENT", 0.25))

    # Directional score band edges (absolute value of weighted score).
    strong_band: float = field(default_factory=lambda: _env_float("STRONG_BAND", 0.50))
    moderate_band: float = field(default_factory=lambda: _env_float("MODERATE_BAND", 0.15))

    # ---- Confidence penalties -------------------------------------------
    conflict_penalty: float = field(default_factory=lambda: _env_float("CONFLICT_PENALTY", 0.30))
    missing_agent_cap: float = field(default_factory=lambda: _env_float("MISSING_AGENT_CAP", 0.65))
    low_quality_cap: float = field(default_factory=lambda: _env_float("LOW_QUALITY_CAP", 0.50))
    no_evidence_cap: float = field(default_factory=lambda: _env_float("NO_EVIDENCE_CAP", 0.55))

    @property
    def weights(self) -> dict[str, float]:
        return {
            "technical": self.weight_technical,
            "fundamental": self.weight_fundamental,
            "sentiment": self.weight_sentiment,
        }

    @property
    def llm_available(self) -> bool:
        return bool(self.use_llm and self.anthropic_api_key)


settings = Settings()
