"""
Risk Engine — deterministic, not an LLM agent.

Two guarantees that matter for the demo:

1. Risk NEVER mutates the market signal. `final_signal` is computed purely
   from agent evidence. Risk only constrains the *recommendation*.
2. Identical market input + different user profile => different
   recommendation. That is the personalization requirement, made visible
   through `personalization` strings.
"""

from __future__ import annotations

from typing import Any

from app.schemas.models import (
    ACTION_LADDER,
    DataQuality,
    Recommendation,
    RiskAssessment,
    RiskLevel,
    UserProfile,
)

TOLERANCE_BASE = {
    "conservative": 0.45,
    "moderate": 0.25,
    "aggressive": 0.10,
}

# Conservative investors are never told to go all-in on a single name.
TOLERANCE_CEILING = {
    "conservative": Recommendation.ACCUMULATE,
    "moderate": Recommendation.BUY,
    "aggressive": Recommendation.BUY,
}

HORIZON_NOTE = {
    "short": "Short investment horizon — near-term volatility carries more weight.",
    "medium": "Medium investment horizon.",
    "long": "Long investment horizon — short-term drawdowns are more tolerable.",
}


class RiskEngine:
    """Scores portfolio + behavioral risk and derives recommendation limits."""

    def assess(
        self,
        symbol: str,
        profile: UserProfile | dict[str, Any] | None,
        market_data: dict[str, Any] | None = None,
        data_quality: DataQuality = DataQuality.HIGH,
    ) -> RiskAssessment:
        if isinstance(profile, dict):
            profile = UserProfile(**profile)
        elif profile is None:
            profile = UserProfile()

        market_data = market_data or {}
        indicators = market_data.get("indicators") or {}

        tolerance = (profile.risk_tolerance or "moderate").strip().lower()
        if tolerance not in TOLERANCE_BASE:
            tolerance = "moderate"

        risk_factors: list[str] = []
        personalization: list[str] = []

        score = TOLERANCE_BASE[tolerance]
        personalization.append(
            f"Risk tolerance on file: {tolerance}."
        )
        personalization.append(
            HORIZON_NOTE.get(
                (profile.investment_horizon or "medium").lower(),
                "Investment horizon not specified.",
            )
        )

        # --- existing exposure -----------------------------------------
        exposure = profile.exposure_to(symbol)
        cap = profile.max_position_pct or 15.0
        if exposure > 0:
            personalization.append(
                f"Existing {symbol} exposure is {exposure:.1f}% of the portfolio "
                f"against a self-declared cap of {cap:.1f}%."
            )
        else:
            personalization.append(f"No current {symbol} position in the portfolio.")

        if exposure >= cap:
            score += 0.30
            risk_factors.append(
                f"Position limit breached: {symbol} is {exposure:.1f}% of the portfolio, "
                f"above the {cap:.1f}% cap — adding would deepen an oversized position."
            )
        elif exposure >= cap * 0.75:
            score += 0.15
            risk_factors.append(
                f"{symbol} exposure ({exposure:.1f}%) is approaching the {cap:.1f}% cap."
            )

        # --- concentration ----------------------------------------------
        concentration = profile.concentration_score
        if concentration is None:
            concentration = self._derive_concentration(profile)
        concentration = max(0.0, min(1.0, float(concentration)))
        if concentration >= 0.7:
            score += 0.20
            risk_factors.append(
                f"Portfolio concentration score is high ({concentration:.2f}); "
                "returns are driven by a small number of holdings."
            )
        elif concentration >= 0.5:
            score += 0.10
            risk_factors.append(
                f"Portfolio concentration score is moderate ({concentration:.2f})."
            )

        # --- cash buffer -------------------------------------------------
        if profile.cash_pct < 5:
            score += 0.08
            risk_factors.append(
                f"Cash buffer is thin ({profile.cash_pct:.1f}%), limiting room to average down."
            )

        # --- market risk --------------------------------------------------
        volatility = self._num(indicators.get("volatility_30d_pct"))
        atr = self._num(indicators.get("atr_pct"))
        if volatility is not None and volatility >= 30:
            score += 0.12
            risk_factors.append(
                f"30-day realised volatility is elevated at {volatility:.1f}%."
            )
        elif atr is not None and atr >= 3:
            score += 0.08
            risk_factors.append(f"Average true range is wide at {atr:.1f}% of price.")

        for flag in market_data.get("risk_flags", []) or []:
            score += 0.10
            risk_factors.append(f"Market data flag: {flag}.")

        # --- behavioral ---------------------------------------------------
        flags = [str(f).lower() for f in (profile.behavioral_flags or [])]
        if "panic_seller" in flags:
            score += 0.10
            risk_factors.append(
                "Behavioral history shows panic-selling during drawdowns."
            )
            personalization.append(
                "Guidance is framed conservatively given a history of selling into weakness."
            )
        if "momentum_chaser" in flags:
            score += 0.08
            risk_factors.append("Behavioral history shows momentum chasing.")
            personalization.append(
                "Momentum-chasing history noted — entry timing guidance is tightened."
            )
        if "overtrader" in flags:
            score += 0.05
            risk_factors.append("Behavioral history shows frequent overtrading.")
        if (profile.experience_level or "").lower() in {"beginner", "novice", "new"}:
            score += 0.07
            personalization.append(
                "Beginner experience level — recommendation biased toward capital preservation."
            )

        # --- degraded data is itself a risk --------------------------------
        if data_quality == DataQuality.LOW:
            score += 0.12
            risk_factors.append(
                "Analysis rests on low-quality input data, which widens the error band."
            )
        elif data_quality == DataQuality.NONE:
            score += 0.20
            risk_factors.append("Critical input data was unavailable for this analysis.")

        score = max(0.0, min(1.0, score))
        level = self._level(score)

        downgrade = {
            RiskLevel.LOW: 0,
            RiskLevel.MODERATE: 0,
            RiskLevel.HIGH: 1,
            RiskLevel.CRITICAL: 2,
        }[level]
        # A breached position limit always suppresses further buying,
        # regardless of how bullish the market signal is.
        if exposure >= cap and cap > 0:
            downgrade = max(downgrade, 1)

        if not risk_factors:
            risk_factors.append("No material portfolio or market risk flags identified.")

        return RiskAssessment(
            risk_level=level,
            risk_score=round(score, 3),
            risk_factors=risk_factors,
            personalization=personalization,
            max_bullish_action=TOLERANCE_CEILING[tolerance],
            downgrade_steps=downgrade,
            exposure_pct=round(exposure, 2),
            concentration_score=round(concentration, 3),
        )

    # ------------------------------------------------------------------

    def apply(
        self, base_action: Recommendation, assessment: RiskAssessment
    ) -> tuple[Recommendation, list[str]]:
        """Constrain a signal-derived action by the risk assessment.

        Risk can only move the action *down* the ladder (toward caution). It
        can never turn a bearish signal into a buy.
        """
        notes: list[str] = []
        index = ACTION_LADDER.index(base_action)
        ceiling_index = ACTION_LADDER.index(assessment.max_bullish_action)

        adjusted = index
        if assessment.downgrade_steps and index > ACTION_LADDER.index(Recommendation.HOLD):
            adjusted = max(ACTION_LADDER.index(Recommendation.HOLD), index - assessment.downgrade_steps)
            if adjusted != index:
                notes.append(
                    f"Risk level {assessment.risk_level.value} moved the action from "
                    f"{ACTION_LADDER[index].value} to {ACTION_LADDER[adjusted].value}; "
                    "the underlying market signal is unchanged."
                )

        if adjusted > ceiling_index:
            notes.append(
                f"A {assessment.max_bullish_action.value} ceiling applies to this risk profile, "
                f"capping the action at {ACTION_LADDER[ceiling_index].value}."
            )
            adjusted = ceiling_index

        return ACTION_LADDER[adjusted], notes

    # ------------------------------------------------------------------

    @staticmethod
    def _derive_concentration(profile: UserProfile) -> float:
        """Herfindahl-style concentration when the profile service omits it."""
        weights = []
        for holding in profile.holdings:
            try:
                weights.append(float(holding.get("weight_pct", 0) or 0) / 100.0)
            except (TypeError, ValueError):
                continue
        if not weights:
            return 0.0
        return min(1.0, sum(w * w for w in weights) * len(weights) / max(len(weights), 1))

    @staticmethod
    def _num(value: Any) -> float | None:
        try:
            if value is None or isinstance(value, bool):
                return None
            result = float(value)
            return result if result == result else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _level(score: float) -> RiskLevel:
        if score >= 0.80:
            return RiskLevel.CRITICAL
        if score >= 0.55:
            return RiskLevel.HIGH
        if score >= 0.32:
            return RiskLevel.MODERATE
        return RiskLevel.LOW
