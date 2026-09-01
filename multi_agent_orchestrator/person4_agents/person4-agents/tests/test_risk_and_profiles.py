"""Tests 9 and 10: risk calculation, and different users on identical inputs."""

from __future__ import annotations

import pytest

from app.api import analyze
from app.risk.risk_engine import RiskEngine
from app.schemas.models import (
    DataQuality,
    Recommendation,
    RiskAssessment,
    RiskLevel,
    UserProfile,
)


class TestRiskEngine:
    def test_conservative_overexposed_user_is_high_risk(self, conservative_profile):
        risk = RiskEngine().assess("RELIANCE", conservative_profile)

        assert risk.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        assert risk.exposure_pct == 22.0
        assert risk.downgrade_steps >= 1
        assert any("cap" in f.lower() or "limit" in f.lower() for f in risk.risk_factors)

    def test_aggressive_diversified_user_is_low_risk(self, aggressive_profile):
        risk = RiskEngine().assess("RELIANCE", aggressive_profile)

        assert risk.risk_level in (RiskLevel.LOW, RiskLevel.MODERATE)
        assert risk.exposure_pct == 4.0
        assert risk.downgrade_steps == 0

    def test_position_limit_breach_is_flagged(self):
        profile = {
            "user_id": "u1",
            "risk_tolerance": "moderate",
            "max_position_pct": 10.0,
            "cash_pct": 20.0,
            "holdings": [{"symbol": "RELIANCE", "weight_pct": 30.0}],
        }
        risk = RiskEngine().assess("RELIANCE", profile)
        assert any("Position limit breached" in f for f in risk.risk_factors)
        assert risk.downgrade_steps >= 1

    def test_market_volatility_raises_risk(self, aggressive_profile):
        calm = RiskEngine().assess("RELIANCE", aggressive_profile,
                                   {"indicators": {"volatility_30d_pct": 14.0}})
        wild = RiskEngine().assess("RELIANCE", aggressive_profile,
                                   {"indicators": {"volatility_30d_pct": 44.0}})
        assert wild.risk_score > calm.risk_score

    def test_degraded_data_raises_risk(self, aggressive_profile):
        clean = RiskEngine().assess("RELIANCE", aggressive_profile, {},
                                    data_quality=DataQuality.HIGH)
        dirty = RiskEngine().assess("RELIANCE", aggressive_profile, {},
                                    data_quality=DataQuality.LOW)
        assert dirty.risk_score > clean.risk_score

    def test_behavioral_flags_personalize_output(self, conservative_profile):
        risk = RiskEngine().assess("RELIANCE", conservative_profile)
        joined = " ".join(risk.personalization + risk.risk_factors).lower()
        assert "panic" in joined

    def test_missing_profile_uses_safe_defaults(self):
        risk = RiskEngine().assess("RELIANCE", None)
        assert isinstance(risk, RiskAssessment)
        assert risk.risk_level in set(RiskLevel)

    def test_concentration_is_derived_when_absent(self):
        profile = UserProfile(
            user_id="u2",
            holdings=[{"symbol": "RELIANCE", "weight_pct": 60.0},
                      {"symbol": "TCS", "weight_pct": 40.0}],
            cash_pct=10.0,
        )
        risk = RiskEngine().assess("RELIANCE", profile)
        assert risk.concentration_score > 0

    def test_risk_only_moves_action_toward_caution(self):
        engine = RiskEngine()
        risky = engine.assess(
            "RELIANCE",
            {
                "risk_tolerance": "conservative",
                "max_position_pct": 5.0,
                "cash_pct": 1.0,
                "concentration_score": 0.9,
                "holdings": [{"symbol": "RELIANCE", "weight_pct": 30.0}],
            },
        )
        # A bearish action is never softened by risk.
        action, _ = engine.apply(Recommendation.SELL, risky)
        assert action == Recommendation.SELL

        # A bullish action is pulled back.
        action, notes = engine.apply(Recommendation.BUY, risky)
        assert action in (Recommendation.HOLD, Recommendation.ACCUMULATE)
        assert notes

    def test_risk_never_pushes_below_hold_on_bullish_signal(self):
        engine = RiskEngine()
        risky = engine.assess(
            "RELIANCE",
            {
                "risk_tolerance": "conservative",
                "max_position_pct": 2.0,
                "cash_pct": 0.0,
                "concentration_score": 1.0,
                "experience_level": "beginner",
                "behavioral_flags": ["panic_seller", "overtrader"],
                "holdings": [{"symbol": "RELIANCE", "weight_pct": 40.0}],
            },
        )
        action, _ = engine.apply(Recommendation.BUY, risky)
        assert action == Recommendation.HOLD, "risk must not invert a bullish signal into a sell"


class TestUserProfileDivergence:
    """Test 10: identical market input, different users, different advice."""

    @pytest.fixture
    async def results(self, market_data, rag_context, conservative_profile, aggressive_profile):
        conservative = await analyze("RELIANCE", market_data, rag_context, conservative_profile)
        aggressive = await analyze("RELIANCE", market_data, rag_context, aggressive_profile)
        return conservative, aggressive

    async def test_same_market_signal_for_both_users(self, results):
        conservative, aggressive = results
        assert conservative.final_signal == aggressive.final_signal
        assert conservative.directional_score == aggressive.directional_score

    async def test_recommendation_differs_by_profile(self, results):
        conservative, aggressive = results
        assert conservative.recommendation != aggressive.recommendation
        assert conservative.recommendation == Recommendation.HOLD
        assert aggressive.recommendation == Recommendation.BUY

    async def test_risk_level_differs_by_profile(self, results):
        conservative, aggressive = results
        assert conservative.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        assert aggressive.risk_level in (RiskLevel.LOW, RiskLevel.MODERATE)

    async def test_personalization_is_explicit_and_user_specific(self, results):
        conservative, aggressive = results
        assert conservative.personalization and aggressive.personalization
        assert "conservative" in " ".join(conservative.personalization).lower()
        assert "aggressive" in " ".join(aggressive.personalization).lower()
        assert conservative.personalization != aggressive.personalization

    async def test_conservative_reasoning_explains_the_downgrade(self, results):
        conservative, _ = results
        joined = " ".join(conservative.reasoning).lower()
        assert "risk level" in joined
        assert "market signal is unchanged" in joined

    async def test_user_id_is_carried_through(self, results):
        conservative, aggressive = results
        assert conservative.user_id == "demo_conservative"
        assert aggressive.user_id == "demo_aggressive"
