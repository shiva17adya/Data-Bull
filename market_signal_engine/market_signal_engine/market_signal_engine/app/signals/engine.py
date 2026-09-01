"""The signal engine: fetch, validate, calculate, combine, explain.

Combination is a transparent weighted vote. Each dimension maps to a score

    BULLISH = +1, NEUTRAL = 0, BEARISH = -1

and the overall score is the weighted mean over the dimensions that could
actually be calculated:

    overall_score = sum(weight_i * score_i) / sum(weight_i)

Renormalising by the available weight means a missing dimension shifts the
result toward the remaining evidence rather than silently dragging it toward
neutral. Classification is then:

    overall_score >= +0.33 -> BULLISH
    overall_score <= -0.33 -> BEARISH
    otherwise              -> NEUTRAL

Confidence is

    confidence = base_confidence * agreement_factor * data_quality_factor

where ``base_confidence`` is the weighted mean of the individual confidences,
``agreement_factor`` is the weighted alignment of each dimension with the final
classification (1.0 if it matches, 0.5 if one step away, 0.0 if opposed), and
``data_quality_factor`` falls as dimensions go missing or data problems are
detected. The whole path is deterministic: identical candles always produce an
identical response.

This module produces analytical market signals. It does not produce
personalised investment advice.
"""

from __future__ import annotations

import logging
from typing import Sequence

from app.config import (
    DEGRADED_DATA_PENALTY,
    MOMENTUM_LOOKBACK,
    OVERALL_BEARISH_THRESHOLD,
    OVERALL_BULLISH_THRESHOLD,
    RSI_PERIOD,
    SIGNAL_MOMENTUM,
    SIGNAL_RSI,
    SIGNAL_VOLUME,
    SIGNAL_WEIGHTS,
    VOLUME_LOOKBACK,
)
from app.data.provider import MarketDataProvider
from app.models.schemas import (
    DataStatus,
    MarketCandle,
    MarketData,
    SignalLabel,
    SignalResponse,
    SignalResult,
    utc_now,
)
from app.signals.common import clamp, round_confidence
from app.signals.momentum import calculate_momentum
from app.signals.rsi import calculate_rsi
from app.signals.volume import calculate_volume_anomaly

logger = logging.getLogger(__name__)

SCORE_BY_LABEL: dict[SignalLabel, int] = {
    SignalLabel.BULLISH: 1,
    SignalLabel.NEUTRAL: 0,
    SignalLabel.BEARISH: -1,
}

# Maximum possible distance between two dimension scores, used to normalise the
# agreement factor onto [0, 1]. Scores live in [-1, +1], so the spread is 2.
MAX_SCORE_SPREAD = 2.0


class SignalEngine:
    """Turns raw market data into a classified, explained signal response."""

    def __init__(self, provider: MarketDataProvider) -> None:
        self._provider = provider

    @property
    def provider(self) -> MarketDataProvider:
        return self._provider

    def analyze(
        self,
        symbol: str,
        lookback: int = MOMENTUM_LOOKBACK,
        volume_lookback: int = VOLUME_LOOKBACK,
        rsi_period: int = RSI_PERIOD,
    ) -> SignalResponse:
        """Produce the full signal response for ``symbol``.

        Raises:
            SymbolNotFoundError: propagated from the provider for unknown symbols.
        """
        logger.info("signal_request_received symbol=%s lookback=%s", symbol, lookback)

        market_data = self._provider.get_market_data(symbol)
        logger.info(
            "market_data_retrieved symbol=%s candles=%d warnings=%d",
            market_data.symbol,
            len(market_data.candles),
            len(market_data.warnings),
        )

        return self.analyze_market_data(
            market_data,
            lookback=lookback,
            volume_lookback=volume_lookback,
            rsi_period=rsi_period,
        )

    def analyze_market_data(
        self,
        market_data: MarketData,
        lookback: int = MOMENTUM_LOOKBACK,
        volume_lookback: int = VOLUME_LOOKBACK,
        rsi_period: int = RSI_PERIOD,
    ) -> SignalResponse:
        """Analyse an already-fetched ``MarketData``. Pure and side-effect free.

        Exposed separately so tests (and any future caller holding its own data)
        can exercise the engine without going through a provider.
        """
        warnings: list[str] = list(market_data.warnings)
        candles = market_data.candles

        if not candles:
            warnings.append("No valid market candles are available for this symbol.")
            logger.warning("no_valid_candles symbol=%s", market_data.symbol)
            return SignalResponse(
                symbol=market_data.symbol,
                timestamp=utc_now(),
                market_data=None,
                signals={},
                overall_signal=SignalLabel.NEUTRAL,
                confidence=0.0,
                reasoning=["No market data was available, so no signal could be produced."],
                data_status=DataStatus.UNAVAILABLE,
                warnings=warnings,
            )

        signals = self._calculate_signals(candles, lookback, volume_lookback, rsi_period)

        for result in signals.values():
            if result.signal is SignalLabel.UNAVAILABLE:
                warnings.extend(result.evidence)

        overall_signal, overall_score, confidence, reasoning = self._combine(
            signals, data_warnings_present=bool(market_data.warnings)
        )

        data_status = self._determine_status(signals, warnings)

        logger.info(
            "signal_calculation_completed symbol=%s overall=%s score=%.3f confidence=%.2f status=%s",
            market_data.symbol,
            overall_signal.value,
            overall_score,
            confidence,
            data_status.value,
        )
        if data_status is not DataStatus.OK:
            logger.warning(
                "degraded_data_detected symbol=%s warnings=%s", market_data.symbol, warnings
            )

        return SignalResponse(
            symbol=market_data.symbol,
            timestamp=utc_now(),
            market_data=market_data.snapshot(),
            signals=signals,
            overall_signal=overall_signal,
            confidence=confidence,
            reasoning=reasoning,
            data_status=data_status,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _calculate_signals(
        self,
        candles: Sequence[MarketCandle],
        lookback: int,
        volume_lookback: int,
        rsi_period: int,
    ) -> dict[str, SignalResult]:
        """Run all three calculators, isolating each from the others' failures."""
        return {
            SIGNAL_MOMENTUM: self._safe_calculate(
                SIGNAL_MOMENTUM, calculate_momentum, candles, lookback
            ),
            SIGNAL_VOLUME: self._safe_calculate(
                SIGNAL_VOLUME, calculate_volume_anomaly, candles, volume_lookback
            ),
            SIGNAL_RSI: self._safe_calculate(SIGNAL_RSI, calculate_rsi, candles, rsi_period),
        }

    @staticmethod
    def _safe_calculate(name, calculator, candles, parameter) -> SignalResult:
        """Never let one calculator take down the whole response."""
        try:
            return calculator(candles, parameter)
        except Exception:  # noqa: BLE001 - deliberate boundary around third-party math
            logger.exception("calculation_failure signal=%s", name)
            from app.signals.common import unavailable

            return unavailable(name, f"The {name} calculation failed unexpectedly.")

    def _combine(
        self,
        signals: dict[str, SignalResult],
        data_warnings_present: bool,
    ) -> tuple[SignalLabel, float, float, list[str]]:
        """Weighted vote across the available dimensions."""
        available = {
            name: result
            for name, result in signals.items()
            if result.signal in SCORE_BY_LABEL
        }

        if not available:
            reasoning = [
                "No signal dimension could be calculated from the available market data.",
                "A NEUTRAL classification is reported with zero confidence rather than a guess.",
            ]
            return SignalLabel.NEUTRAL, 0.0, 0.0, reasoning

        weights = {name: SIGNAL_WEIGHTS[name] for name in available}
        available_weight = sum(weights.values())
        total_weight = sum(SIGNAL_WEIGHTS.values())

        overall_score = (
            sum(weights[name] * SCORE_BY_LABEL[result.signal] for name, result in available.items())
            / available_weight
        )

        overall_signal = self._classify_overall(overall_score)

        base_confidence = (
            sum(weights[name] * result.confidence for name, result in available.items())
            / available_weight
        )

        # Agreement is measured against the final classification, not the raw
        # weighted mean. Each dimension scores 1.0 if it matches the overall
        # label, 0.5 if it is one step away, and 0.0 if it points the opposite
        # way. Anchoring on the mean instead would rank a three-way split
        # (+1/0/-1) above a two-versus-one split (+1/+1/-1), which is backwards.
        overall_label_score = SCORE_BY_LABEL[overall_signal]
        agreement_factor = clamp(
            sum(
                weights[name]
                * (
                    1.0
                    - abs(SCORE_BY_LABEL[result.signal] - overall_label_score)
                    / MAX_SCORE_SPREAD
                )
                for name, result in available.items()
            )
            / available_weight
        )

        data_quality_factor = available_weight / total_weight
        if data_warnings_present:
            data_quality_factor *= DEGRADED_DATA_PENALTY

        confidence = round_confidence(base_confidence * agreement_factor * data_quality_factor)

        reasoning = self._build_reasoning(
            signals, available, overall_signal, overall_score, agreement_factor
        )

        return overall_signal, overall_score, confidence, reasoning

    @staticmethod
    def _classify_overall(overall_score: float) -> SignalLabel:
        if overall_score >= OVERALL_BULLISH_THRESHOLD:
            return SignalLabel.BULLISH
        if overall_score <= OVERALL_BEARISH_THRESHOLD:
            return SignalLabel.BEARISH
        return SignalLabel.NEUTRAL

    @staticmethod
    def _build_reasoning(
        signals: dict[str, SignalResult],
        available: dict[str, SignalResult],
        overall_signal: SignalLabel,
        overall_score: float,
        agreement_factor: float,
    ) -> list[str]:
        """One plain-language line per dimension, then the combination summary."""
        descriptions = {
            SIGNAL_MOMENTUM: {
                SignalLabel.BULLISH: "Price momentum is positive.",
                SignalLabel.BEARISH: "Price momentum is negative.",
                SignalLabel.NEUTRAL: "Price momentum is flat.",
            },
            SIGNAL_VOLUME: {
                SignalLabel.BULLISH: "Trading volume is elevated alongside rising prices.",
                SignalLabel.BEARISH: "Trading volume is elevated alongside falling prices.",
                SignalLabel.NEUTRAL: "Trading volume does not indicate a directional bias.",
            },
            SIGNAL_RSI: {
                SignalLabel.BULLISH: "RSI indicates oversold pressure.",
                SignalLabel.BEARISH: "RSI indicates overbought pressure.",
                SignalLabel.NEUTRAL: "RSI is within its neutral band.",
            },
        }

        reasoning: list[str] = []
        for name, result in signals.items():
            if result.signal in SCORE_BY_LABEL:
                reasoning.append(descriptions[name][result.signal])
            else:
                reasoning.append(f"The {name} dimension was unavailable and was excluded.")

        supporting = sum(
            1 for result in available.values() if result.signal is overall_signal
        )
        reasoning.append(
            f"{supporting} of {len(available)} available signal dimensions support the "
            f"{overall_signal.value} classification (weighted score {overall_score:+.2f})."
        )

        if agreement_factor < 1.0:
            reasoning.append(
                "The dimensions do not fully agree, so overall confidence has been reduced."
            )

        return reasoning

    @staticmethod
    def _determine_status(signals: dict[str, SignalResult], warnings: list[str]) -> DataStatus:
        computed = [r for r in signals.values() if r.signal in SCORE_BY_LABEL]
        if not computed:
            return DataStatus.UNAVAILABLE
        if warnings or len(computed) < len(signals):
            return DataStatus.DEGRADED
        return DataStatus.OK


def market_data_status(market_data: MarketData) -> DataStatus:
    """Status for the raw /market endpoint (no signals involved)."""
    if not market_data.candles:
        return DataStatus.UNAVAILABLE
    if market_data.warnings:
        return DataStatus.DEGRADED
    return DataStatus.OK
