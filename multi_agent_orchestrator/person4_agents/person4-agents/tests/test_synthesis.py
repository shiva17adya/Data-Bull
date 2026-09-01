"""Tests 5 and 6: synthesis weighting, and explicit conflict resolution."""

from __future__ import annotations

import pytest

from app.schemas.models import (
    AgentOutput,
    AgentStatus,
    DataQuality,
    Evidence,
    FinalSignal,
    RiskLevel,
    Signal,
)
from app.risk.risk_engine import RiskEngine
from app.synthesis.synthesizer import Synthesizer


def make_agent(
    name: str,
    signal: Signal,
    confidence: float = 0.8,
    quality: DataQuality = DataQuality.HIGH,
    status: AgentStatus = AgentStatus.SUCCESS,
    evidence: list[Evidence] | None = None,
) -> AgentOutput:
    return AgentOutput(
        agent=name,
        status=status,
        signal=signal,
        confidence=confidence,
        reasoning=[f"{name} says {signal.value}"],
        evidence=evidence or [],
        data_quality=quality,
    )


@pytest.fixture
def neutral_risk():
    return RiskEngine().assess("RELIANCE", {"risk_tolerance": "moderate", "cash_pct": 20.0})


class TestWeightedScoring:
    def test_unanimous_bullish_gives_bullish(self, neutral_risk):
        outputs = [
            make_agent("technical", Signal.BULLISH, 0.85),
            make_agent("fundamental", Signal.BULLISH, 0.80),
            make_agent("sentiment", Signal.BULLISH, 0.75),
        ]
        outcome = Synthesizer().synthesize("RELIANCE", outputs, neutral_risk)
        assert outcome.final_signal == FinalSignal.BULLISH
        assert outcome.directional_score > 0.5

    def test_unanimous_bearish_gives_bearish(self, neutral_risk):
        outputs = [
            make_agent("technical", Signal.BEARISH, 0.85),
            make_agent("fundamental", Signal.BEARISH, 0.80),
            make_agent("sentiment", Signal.BEARISH, 0.75),
        ]
        outcome = Synthesizer().synthesize("RELIANCE", outputs, neutral_risk)
        assert outcome.final_signal == FinalSignal.BEARISH
        assert outcome.directional_score < -0.5

    def test_weights_match_configuration(self, neutral_risk):
        """Score must equal Σ(weight × confidence × direction) / Σ(weight)."""
        outputs = [
            make_agent("technical", Signal.BULLISH, 0.80),
            make_agent("fundamental", Signal.BEARISH, 0.60),
            make_agent("sentiment", Signal.NEUTRAL, 0.50),
        ]
        outcome = Synthesizer().synthesize("RELIANCE", outputs, neutral_risk)
        expected = (0.35 * 0.80 * 1 + 0.40 * 0.60 * -1 + 0.25 * 0.50 * 0) / (0.35 + 0.40 + 0.25)
        assert outcome.directional_score == pytest.approx(expected, abs=1e-3)

    def test_moderate_band_is_reachable(self, neutral_risk):
        outputs = [
            make_agent("technical", Signal.BULLISH, 0.40),
            make_agent("fundamental", Signal.BULLISH, 0.35),
            make_agent("sentiment", Signal.NEUTRAL, 0.40),
        ]
        outcome = Synthesizer().synthesize("RELIANCE", outputs, neutral_risk)
        assert outcome.final_signal == FinalSignal.MODERATELY_BULLISH

    def test_fundamental_outweighs_technical(self, neutral_risk):
        """Fundamental carries 0.40 vs technical 0.35 at equal confidence."""
        outputs = [
            make_agent("technical", Signal.BULLISH, 0.70),
            make_agent("fundamental", Signal.BEARISH, 0.70),
        ]
        outcome = Synthesizer().synthesize("RELIANCE", outputs, neutral_risk)
        assert outcome.directional_score < 0

    def test_agreement_raises_confidence_over_conflict(self, neutral_risk):
        # Both sides carry citations so the comparison isolates the
        # agreement/conflict factor rather than the no-evidence cap.
        cited = [Evidence(source="filing.pdf", section="Outlook", text="…", score=0.9)]

        agree = Synthesizer().synthesize(
            "RELIANCE",
            [
                make_agent("technical", Signal.BULLISH, 0.80),
                make_agent("fundamental", Signal.BULLISH, 0.80, evidence=cited),
                make_agent("sentiment", Signal.BULLISH, 0.80),
            ],
            neutral_risk,
        )
        conflict = Synthesizer().synthesize(
            "RELIANCE",
            [
                make_agent("technical", Signal.BULLISH, 0.80),
                make_agent("fundamental", Signal.BEARISH, 0.80, evidence=cited),
                make_agent("sentiment", Signal.BULLISH, 0.80),
            ],
            neutral_risk,
        )
        assert agree.confidence > conflict.confidence

    def test_uncited_analysis_is_capped(self, neutral_risk):
        """No document citations anywhere => confidence is capped."""
        outputs = [
            make_agent("technical", Signal.BULLISH, 0.95),
            make_agent("fundamental", Signal.BULLISH, 0.95),
            make_agent("sentiment", Signal.BULLISH, 0.95),
        ]
        outcome = Synthesizer().synthesize("RELIANCE", outputs, neutral_risk)
        assert outcome.confidence <= 0.55
        assert any("No source documents" in r for r in outcome.reasoning)

    def test_no_usable_agents_yields_zero_confidence(self, neutral_risk):
        outputs = [
            make_agent("technical", Signal.NEUTRAL, 0.0, DataQuality.NONE, AgentStatus.FAILED),
            make_agent("fundamental", Signal.NEUTRAL, 0.0, DataQuality.NONE, AgentStatus.FAILED),
            make_agent("sentiment", Signal.NEUTRAL, 0.0, DataQuality.NONE, AgentStatus.FAILED),
        ]
        outcome = Synthesizer().synthesize("RELIANCE", outputs, neutral_risk)
        assert outcome.confidence == 0.0
        assert outcome.final_signal == FinalSignal.NEUTRAL
        assert outcome.data_quality == DataQuality.NONE
        assert any("No agent produced a usable view" in r for r in outcome.reasoning)


class TestConflictResolution:
    """Test 6: disagreement must be named, explained and priced in."""

    @pytest.fixture
    def conflicting(self):
        return [
            make_agent("technical", Signal.BULLISH, 0.82),
            make_agent(
                "fundamental",
                Signal.BEARISH,
                0.78,
                evidence=[
                    Evidence(
                        source="SEBI_show_cause_notice.pdf",
                        section="Proceedings",
                        text="A monetary penalty may follow.",
                        score=0.9,
                    )
                ],
            ),
            make_agent("sentiment", Signal.BULLISH, 0.55),
        ]

    def test_conflict_is_detected(self, conflicting, neutral_risk):
        outcome = Synthesizer().synthesize("RELIANCE", conflicting, neutral_risk)
        assert outcome.conflict["conflicted"] is True
        assert set(outcome.conflict["bullish_agents"]) == {"technical", "sentiment"}
        assert outcome.conflict["bearish_agents"] == ["fundamental"]

    def test_reasoning_states_the_conflict(self, conflicting, neutral_risk):
        outcome = Synthesizer().synthesize("RELIANCE", conflicting, neutral_risk)
        joined = " ".join(outcome.reasoning).lower()
        assert "disagree" in joined
        assert "strongest" in joined

    def test_reasoning_names_the_stronger_evidence(self, conflicting, neutral_risk):
        outcome = Synthesizer().synthesize("RELIANCE", conflicting, neutral_risk)
        joined = " ".join(outcome.reasoning)
        assert outcome.conflict["strongest_agent"] is not None
        assert "cited source excerpt" in joined or "without document citations" in joined

    def test_conflict_reduces_confidence(self, conflicting, neutral_risk):
        conflicted = Synthesizer().synthesize("RELIANCE", conflicting, neutral_risk)
        aligned = Synthesizer().synthesize(
            "RELIANCE",
            [
                make_agent("technical", Signal.BULLISH, 0.82),
                make_agent(
                    "fundamental",
                    Signal.BULLISH,
                    0.78,
                    evidence=[
                        Evidence(
                            source="SEBI_show_cause_notice.pdf",
                            section="Proceedings",
                            text="A monetary penalty may follow.",
                            score=0.9,
                        )
                    ],
                ),
                make_agent("sentiment", Signal.BULLISH, 0.55),
            ],
            neutral_risk,
        )
        assert conflicted.confidence < aligned.confidence

    def test_dominant_side_wins_direction(self, neutral_risk):
        """A high-conviction fundamental bear beats a weak technical bull."""
        outputs = [
            make_agent("technical", Signal.BULLISH, 0.30),
            make_agent("fundamental", Signal.BEARISH, 0.90),
        ]
        outcome = Synthesizer().synthesize("RELIANCE", outputs, neutral_risk)
        assert outcome.conflict["dominant_side"] == "bearish"
        assert outcome.directional_score < 0
        assert outcome.final_signal in (
            FinalSignal.BEARISH,
            FinalSignal.MODERATELY_BEARISH,
        )
