"""
Technical Agent.

Interprets indicators supplied by the MarketSignalProvider. It deliberately
does NOT compute RSI/SMA/etc. — the signal engine owns that. This agent turns
numbers into a directional read with stated confidence.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from app.agents.base_agent import BaseAgent
from app.schemas.models import AgentOutput, AgentStatus, DataQuality, Signal

# Indicators the agent knows how to read, in priority order.
KNOWN_INDICATORS = [
    "rsi_14",
    "momentum_5d_pct",
    "momentum_20d_pct",
    "volume_ratio_20d",
    "sma_20",
    "sma_50",
    "sma_200",
    "macd_histogram",
    "atr_pct",
    "volatility_30d_pct",
]

SYSTEM_PROMPT = (
    "You are a technical analysis agent inside a multi-agent investment research system. "
    "You are given pre-computed indicators. Interpret them; do not invent numbers. "
    "Respond with ONLY a JSON object: "
    '{"signal": "BULLISH|NEUTRAL|BEARISH", "confidence": 0.0-1.0, "reasoning": ["...", "..."]}. '
    "Each reasoning string must cite a specific indicator value you were given."
)


def _as_float(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result else None  # filter NaN


class TechnicalAgent(BaseAgent):
    name = "technical"

    async def analyze(self, symbol: str, context: dict[str, Any]) -> AgentOutput:
        market = context.get("market_data") or {}
        indicators_raw = market.get("indicators") or {}
        if not isinstance(indicators_raw, dict):
            indicators_raw = {}

        # Tolerate flat payloads where indicators sit at the top level.
        if not indicators_raw:
            indicators_raw = {k: market[k] for k in KNOWN_INDICATORS if k in market}

        ind: dict[str, float] = {}
        for key in KNOWN_INDICATORS:
            parsed = _as_float(indicators_raw.get(key))
            if parsed is not None:
                ind[key] = parsed

        price = _as_float(market.get("price")) or _as_float(indicators_raw.get("price"))
        feed_status = str(market.get("feed_status", "ok")).lower()

        present = len(ind)
        if present == 0:
            return self.insufficient(
                "No usable technical indicators were supplied by the market feed, "
                "so no technical view can be formed.",
                data_quality=DataQuality.NONE,
            )

        deterministic = self._deterministic(symbol, ind, price, present, feed_status)

        if deterministic.status == AgentStatus.SUCCESS:
            prompt = (
                f"Symbol: {symbol}\n"
                f"Latest price: {price}\n"
                f"Indicators: {json.dumps(ind, indent=2)}\n"
                f"Feed status: {feed_status}\n"
                f"Indicator coverage: {present}/{len(KNOWN_INDICATORS)}\n\n"
                "Give a directional technical read."
            )
            return await self.maybe_llm_refine(SYSTEM_PROMPT, prompt, deterministic)
        return deterministic

    # ------------------------------------------------------------------

    def _deterministic(
        self,
        symbol: str,
        ind: dict[str, float],
        price: Optional[float],
        present: int,
        feed_status: str,
    ) -> AgentOutput:
        score = 0.0
        weight_used = 0.0
        reasoning: list[str] = []

        # --- momentum ---------------------------------------------------
        momentum = ind.get("momentum_20d_pct", ind.get("momentum_5d_pct"))
        if momentum is not None:
            horizon = "20-day" if "momentum_20d_pct" in ind else "5-day"
            contrib = max(-1.0, min(1.0, momentum / 8.0))
            score += 0.30 * contrib
            weight_used += 0.30
            direction = "positive" if momentum > 0 else "negative"
            reasoning.append(
                f"{horizon} price momentum is {momentum:+.1f}%, a {direction} trend contribution."
            )

        # --- RSI --------------------------------------------------------
        rsi = ind.get("rsi_14")
        if rsi is not None:
            if rsi >= 70:
                contrib, note = -0.4, f"RSI(14) at {rsi:.1f} is overbought, pullback risk."
            elif rsi >= 55:
                contrib, note = 0.7, f"RSI(14) at {rsi:.1f} shows healthy buying strength."
            elif rsi > 45:
                contrib, note = 0.0, f"RSI(14) at {rsi:.1f} is neutral."
            elif rsi > 30:
                contrib, note = -0.6, f"RSI(14) at {rsi:.1f} shows fading momentum."
            else:
                contrib, note = 0.3, f"RSI(14) at {rsi:.1f} is oversold, mean-reversion possible."
            score += 0.25 * contrib
            weight_used += 0.25
            reasoning.append(note)

        # --- moving average structure -----------------------------------
        sma20, sma50 = ind.get("sma_20"), ind.get("sma_50")
        sma200 = ind.get("sma_200")
        if price is not None and sma50 is not None:
            above = price > sma50
            contrib = 0.6 if above else -0.6
            if sma200 is not None:
                if price > sma200 and above:
                    contrib = 1.0
                elif price < sma200 and not above:
                    contrib = -1.0
            score += 0.25 * contrib
            weight_used += 0.25
            rel = "above" if above else "below"
            reasoning.append(
                f"Price {price:.2f} is trading {rel} the 50-day SMA ({sma50:.2f})"
                + (f" and the 200-day SMA ({sma200:.2f})." if sma200 is not None else ".")
            )
        elif sma20 is not None and sma50 is not None:
            contrib = 0.6 if sma20 > sma50 else -0.6
            score += 0.25 * contrib
            weight_used += 0.25
            cross = "above" if sma20 > sma50 else "below"
            reasoning.append(f"20-day SMA sits {cross} the 50-day SMA, a trend-following cue.")

        # --- volume anomaly (confirmation, not direction) ---------------
        volume_ratio = ind.get("volume_ratio_20d")
        if volume_ratio is not None:
            weight_used += 0.10
            if volume_ratio >= 1.5:
                score += 0.10 * (0.8 if score >= 0 else -0.8)
                reasoning.append(
                    f"Volume is {volume_ratio:.2f}x the 20-day average, confirming the move."
                )
            elif volume_ratio <= 0.7:
                reasoning.append(
                    f"Volume is only {volume_ratio:.2f}x the 20-day average — weak conviction."
                )
            else:
                reasoning.append(f"Volume at {volume_ratio:.2f}x average is unremarkable.")

        # --- MACD --------------------------------------------------------
        macd = ind.get("macd_histogram")
        if macd is not None:
            contrib = max(-1.0, min(1.0, macd / 5.0))
            score += 0.10 * contrib
            weight_used += 0.10
            reasoning.append(
                f"MACD histogram at {macd:+.2f} "
                f"{'supports' if macd > 0 else 'weighs against'} the upside case."
            )

        normalized = score / weight_used if weight_used else 0.0

        if normalized >= 0.20:
            signal = Signal.BULLISH
        elif normalized <= -0.20:
            signal = Signal.BEARISH
        else:
            signal = Signal.NEUTRAL

        quality = self._quality(present, feed_status)

        # Volatility widens uncertainty rather than changing direction.
        volatility = ind.get("volatility_30d_pct")
        confidence = min(0.92, 0.35 + abs(normalized) * 0.6)
        if volatility is not None and volatility > 30:
            confidence *= 0.9
            reasoning.append(
                f"30-day volatility of {volatility:.1f}% is elevated, so the read is held loosely."
            )
        if quality == DataQuality.MEDIUM:
            confidence *= 0.9
        elif quality == DataQuality.LOW:
            confidence *= 0.75

        if quality == DataQuality.LOW:
            reasoning.append(
                f"Only {present} of {len(KNOWN_INDICATORS)} expected indicators were available; "
                "confidence reduced accordingly."
            )

        status = (
            AgentStatus.INSUFFICIENT_DATA
            if present < 2 or quality == DataQuality.NONE
            else AgentStatus.SUCCESS
        )
        if status == AgentStatus.INSUFFICIENT_DATA:
            reasoning.append(
                "Too few indicators to form a reliable technical view; reporting neutral."
            )
            signal = Signal.NEUTRAL
            confidence = min(confidence, 0.2)

        return AgentOutput(
            agent=self.name,
            status=status,
            signal=signal,
            confidence=round(confidence, 3),
            reasoning=reasoning,
            evidence=[],
            data_quality=quality,
        )

    @staticmethod
    def _quality(present: int, feed_status: str) -> DataQuality:
        if present == 0:
            return DataQuality.NONE
        if feed_status in {"stale", "degraded", "partial"}:
            return DataQuality.LOW if present < 5 else DataQuality.MEDIUM
        if present >= 6:
            return DataQuality.HIGH
        if present >= 4:
            return DataQuality.MEDIUM
        return DataQuality.LOW
