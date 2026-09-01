"""
Synthesis layer.

Takes the surviving agent outputs plus the risk assessment and produces the
final structured result. Three rules drive the design:

* The directional signal comes from agent evidence ONLY. Risk never touches it.
* Conflicts are named explicitly, and the reasoning says which side is stronger
  and why.
* Confidence falls when agents are missing, data is degraded, or agents
  disagree. The system does not claim certainty it has not earned.
"""

from __future__ import annotations

from typing import Any, Optional

from app.config import Settings, settings as default_settings
from app.schemas.models import (
    ACTION_LADDER,
    QUALITY_FACTOR,
    SIGNAL_VALUE,
    AgentOutput,
    AgentStatus,
    DataQuality,
    Evidence,
    FinalSignal,
    Recommendation,
    RiskAssessment,
    Signal,
)

BASE_ACTION: dict[FinalSignal, Recommendation] = {
    FinalSignal.BULLISH: Recommendation.BUY,
    FinalSignal.MODERATELY_BULLISH: Recommendation.ACCUMULATE,
    FinalSignal.NEUTRAL: Recommendation.HOLD,
    FinalSignal.MODERATELY_BEARISH: Recommendation.REDUCE,
    FinalSignal.BEARISH: Recommendation.SELL,
}

AGENT_LABEL = {
    "technical": "Technical",
    "fundamental": "Fundamental (RAG-grounded)",
    "sentiment": "Sentiment",
}


class SynthesisOutcome:
    """Plain container so the orchestrator can build the trace + final result."""

    def __init__(
        self,
        final_signal: FinalSignal,
        directional_score: float,
        confidence: float,
        recommendation: Recommendation,
        reasoning: list[str],
        sources: list[Evidence],
        data_quality: DataQuality,
        conflict: dict[str, Any],
        risk_notes: list[str],
    ):
        self.final_signal = final_signal
        self.directional_score = directional_score
        self.confidence = confidence
        self.recommendation = recommendation
        self.reasoning = reasoning
        self.sources = sources
        self.data_quality = data_quality
        self.conflict = conflict
        self.risk_notes = risk_notes


class Synthesizer:
    def __init__(self, config: Optional[Settings] = None):
        self.settings = config or default_settings
        self.weights = self.settings.weights

    # ------------------------------------------------------------------

    def synthesize(
        self,
        symbol: str,
        agent_outputs: list[AgentOutput],
        risk: RiskAssessment,
    ) -> SynthesisOutcome:
        contributors = [a for a in agent_outputs if a.usable]
        missing = [a for a in agent_outputs if not a.usable]

        score, participating_weight = self._directional_score(contributors)
        final_signal = self._band(score)
        conflict = self._analyze_conflict(contributors)
        data_quality = self._overall_quality(agent_outputs)
        confidence = self._confidence(
            contributors, missing, conflict, data_quality, participating_weight
        )

        reasoning = self._build_reasoning(
            symbol, contributors, missing, score, final_signal, conflict, confidence
        )

        base_action = BASE_ACTION[final_signal]
        recommendation, risk_notes = self._apply_risk(base_action, risk, confidence)
        reasoning.extend(risk_notes)

        sources = self._collect_sources(contributors)
        if not sources:
            reasoning.append(
                "No source documents were cited in this analysis, so the fundamental "
                "picture is unverified."
            )

        return SynthesisOutcome(
            final_signal=final_signal,
            directional_score=round(score, 4),
            confidence=round(confidence, 3),
            recommendation=recommendation,
            reasoning=reasoning,
            sources=sources,
            data_quality=data_quality,
            conflict=conflict,
            risk_notes=risk_notes,
        )

    # ------------------------------------------------------------------
    # Directional score
    # ------------------------------------------------------------------

    def _directional_score(self, contributors: list[AgentOutput]) -> tuple[float, float]:
        """Confidence-scaled weighted mean of BULLISH(+1)/NEUTRAL(0)/BEARISH(-1)."""
        total_weight = sum(self.weights.get(a.agent, 0.0) for a in contributors)
        if total_weight <= 0:
            return 0.0, 0.0
        score = 0.0
        for agent in contributors:
            weight = self.weights.get(agent.agent, 0.0)
            score += weight * agent.confidence * SIGNAL_VALUE[agent.signal]
        return score / total_weight, total_weight

    def _band(self, score: float) -> FinalSignal:
        strong = self.settings.strong_band
        moderate = self.settings.moderate_band
        if score >= strong:
            return FinalSignal.BULLISH
        if score >= moderate:
            return FinalSignal.MODERATELY_BULLISH
        if score <= -strong:
            return FinalSignal.BEARISH
        if score <= -moderate:
            return FinalSignal.MODERATELY_BEARISH
        return FinalSignal.NEUTRAL

    # ------------------------------------------------------------------
    # Conflict
    # ------------------------------------------------------------------

    def _analyze_conflict(self, contributors: list[AgentOutput]) -> dict[str, Any]:
        bulls = [a for a in contributors if a.signal == Signal.BULLISH]
        bears = [a for a in contributors if a.signal == Signal.BEARISH]

        def mass(group: list[AgentOutput]) -> float:
            return sum(
                self.weights.get(a.agent, 0.0) * a.confidence * QUALITY_FACTOR[a.data_quality]
                for a in group
            )

        bull_mass, bear_mass = mass(bulls), mass(bears)
        conflicted = bool(bulls and bears)
        total = bull_mass + bear_mass

        intensity = 0.0
        if conflicted and total > 0:
            intensity = min(bull_mass, bear_mass) / total  # 0 .. 0.5

        strongest = None
        if conflicted:
            dominant = bulls if bull_mass >= bear_mass else bears
            strongest = max(
                dominant,
                key=lambda a: self.weights.get(a.agent, 0.0)
                * a.confidence
                * QUALITY_FACTOR[a.data_quality],
            )

        return {
            "conflicted": conflicted,
            "intensity": round(intensity, 3),
            "bullish_agents": [a.agent for a in bulls],
            "bearish_agents": [a.agent for a in bears],
            "bullish_mass": round(bull_mass, 4),
            "bearish_mass": round(bear_mass, 4),
            "dominant_side": (
                None if not conflicted else ("bullish" if bull_mass >= bear_mass else "bearish")
            ),
            "strongest_agent": strongest.agent if strongest else None,
        }

    # ------------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------------

    def _confidence(
        self,
        contributors: list[AgentOutput],
        missing: list[AgentOutput],
        conflict: dict[str, Any],
        data_quality: DataQuality,
        participating_weight: float,
    ) -> float:
        if not contributors:
            return 0.0

        # 1. Quality-adjusted, weight-averaged agent confidence.
        weighted = sum(
            self.weights.get(a.agent, 0.0) * a.confidence * QUALITY_FACTOR[a.data_quality]
            for a in contributors
        )
        confidence = weighted / participating_weight if participating_weight else 0.0

        # 2. Coverage: missing agents shrink confidence.
        total_weight = sum(self.weights.values())
        coverage = participating_weight / total_weight if total_weight else 0.0
        confidence *= 0.60 + 0.40 * coverage

        # 3. Agreement bonus / conflict penalty.
        if conflict["conflicted"]:
            confidence *= 1.0 - self.settings.conflict_penalty * (2 * conflict["intensity"])
        elif len(contributors) >= 2 and len({a.signal for a in contributors}) == 1:
            confidence *= 1.15

        # 4. Hard caps — never claim high confidence on thin data.
        if missing:
            confidence = min(confidence, self.settings.missing_agent_cap)
        if data_quality == DataQuality.LOW:
            confidence = min(confidence, self.settings.low_quality_cap)
        if not any(a.evidence for a in contributors):
            confidence = min(confidence, self.settings.no_evidence_cap)

        return max(0.0, min(0.95, confidence))

    # ------------------------------------------------------------------
    # Quality
    # ------------------------------------------------------------------

    def _overall_quality(self, agent_outputs: list[AgentOutput]) -> DataQuality:
        total_weight = sum(self.weights.values())
        if total_weight <= 0:
            return DataQuality.NONE
        achieved = sum(
            self.weights.get(a.agent, 0.0) * QUALITY_FACTOR[a.data_quality]
            for a in agent_outputs
            if a.usable
        )
        ratio = achieved / total_weight
        if ratio >= 0.85:
            return DataQuality.HIGH
        if ratio >= 0.60:
            return DataQuality.MEDIUM
        if ratio > 0.0:
            return DataQuality.LOW
        return DataQuality.NONE

    # ------------------------------------------------------------------
    # Narrative
    # ------------------------------------------------------------------

    def _build_reasoning(
        self,
        symbol: str,
        contributors: list[AgentOutput],
        missing: list[AgentOutput],
        score: float,
        final_signal: FinalSignal,
        conflict: dict[str, Any],
        confidence: float,
    ) -> list[str]:
        reasoning: list[str] = []

        if not contributors:
            reasoning.append(
                f"No agent produced a usable view for {symbol}. The system is reporting "
                "NEUTRAL with zero confidence rather than guessing."
            )
            return reasoning

        parts = [
            f"{AGENT_LABEL.get(a.agent, a.agent.title())} {a.signal.value.lower()} "
            f"(confidence {a.confidence:.2f}, weight {self.weights.get(a.agent, 0):.2f}, "
            f"data {a.data_quality.value.lower()})"
            for a in contributors
        ]
        reasoning.append(
            f"Weighted directional score for {symbol} is {score:+.2f}, giving "
            f"{final_signal.value}. Contributing views: " + "; ".join(parts) + "."
        )

        if conflict["conflicted"]:
            bull_names = ", ".join(AGENT_LABEL.get(a, a) for a in conflict["bullish_agents"])
            bear_names = ", ".join(AGENT_LABEL.get(a, a) for a in conflict["bearish_agents"])
            strongest = conflict["strongest_agent"]
            strongest_output = next(
                (a for a in contributors if a.agent == strongest), None
            )
            reasoning.append(
                f"Agents disagree: {bull_names} read bullish while {bear_names} read bearish. "
                f"Resolved in favour of the {conflict['dominant_side']} side "
                f"(weighted mass {max(conflict['bullish_mass'], conflict['bearish_mass']):.3f} "
                f"vs {min(conflict['bullish_mass'], conflict['bearish_mass']):.3f})."
            )
            if strongest_output is not None:
                basis = (
                    f"{len(strongest_output.evidence)} cited source excerpt(s)"
                    if strongest_output.evidence
                    else "indicator-derived analysis without document citations"
                )
                reasoning.append(
                    f"The strongest single input is the "
                    f"{AGENT_LABEL.get(strongest, strongest)} agent, carrying the highest "
                    f"weight × confidence × data-quality product and backed by {basis}. "
                    "Confidence has been reduced because the disagreement is unresolved."
                )
        elif len({a.signal for a in contributors}) == 1 and len(contributors) >= 2:
            reasoning.append(
                "All contributing agents agree on direction, which raises confidence in the read."
            )

        if missing:
            details = ", ".join(
                f"{AGENT_LABEL.get(a.agent, a.agent)} ({a.status.value})" for a in missing
            )
            reasoning.append(
                f"Operating with degraded coverage — unavailable inputs: {details}. "
                "The result is still valid but rests on a narrower base, so confidence is capped."
            )

        reasoning.append(
            f"Overall confidence in this read is {confidence:.2f}."
        )
        return reasoning

    # ------------------------------------------------------------------

    def _apply_risk(
        self,
        base_action: Recommendation,
        risk: RiskAssessment,
        confidence: float,
    ) -> tuple[Recommendation, list[str]]:
        from app.risk.risk_engine import RiskEngine

        recommendation, notes = RiskEngine().apply(base_action, risk)

        # Low confidence should not produce decisive action either.
        if confidence < 0.35:
            hold_index = ACTION_LADDER.index(Recommendation.HOLD)
            current = ACTION_LADDER.index(recommendation)
            if current != hold_index:
                notes.append(
                    f"Confidence of {confidence:.2f} is too low to justify "
                    f"{recommendation.value}; defaulting to HOLD until better data is available."
                )
                recommendation = Recommendation.HOLD
        return recommendation, notes

    # ------------------------------------------------------------------

    @staticmethod
    def _collect_sources(contributors: list[AgentOutput]) -> list[Evidence]:
        seen: set[tuple[str, str, str]] = set()
        sources: list[Evidence] = []
        for agent in contributors:
            for item in agent.evidence:
                key = (item.source, item.section, item.text[:80])
                if key in seen:
                    continue
                seen.add(key)
                sources.append(item)
        return sources
