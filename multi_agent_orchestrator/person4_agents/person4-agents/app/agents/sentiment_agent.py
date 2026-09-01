"""
Sentiment Agent.

Consumes news / headline / behavioral sentiment supplied upstream. Headlines
are cited as evidence so the frontend can show what drove the read.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from app.agents.base_agent import BaseAgent
from app.schemas.models import AgentOutput, AgentStatus, DataQuality, Evidence, Signal

POSITIVE_WORDS = {
    "surge", "surges", "jump", "jumps", "rally", "rallies", "beat", "beats",
    "record", "upgrade", "upgraded", "profit", "gains", "gain", "wins", "win",
    "expansion", "approval", "approved", "bullish", "outperform", "strong",
    "boost", "boosts", "high", "optimism", "recovery",
}

NEGATIVE_WORDS = {
    "plunge", "plunges", "slump", "slumps", "fall", "falls", "drop", "drops",
    "miss", "misses", "downgrade", "downgraded", "loss", "losses", "probe",
    "penalty", "fine", "lawsuit", "bearish", "underperform", "weak", "concern",
    "concerns", "selloff", "warning", "warns", "cut", "cuts", "scrutiny",
}


def _as_float(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result else None


SYSTEM_PROMPT = (
    "You are a market sentiment agent inside a multi-agent investment system. "
    "You are given headlines and sentiment scores. Judge the prevailing tone and whether it is "
    "likely already priced in. Respond with ONLY a JSON object: "
    '{"signal": "BULLISH|NEUTRAL|BEARISH", "confidence": 0.0-1.0, "reasoning": ["...", "..."]}. '
    "Reference specific headlines. Do not invent headlines."
)


class SentimentAgent(BaseAgent):
    name = "sentiment"

    async def analyze(self, symbol: str, context: dict[str, Any]) -> AgentOutput:
        market = context.get("market_data") or {}
        sentiment_ctx = context.get("sentiment_context")
        if not isinstance(sentiment_ctx, dict):
            sentiment_ctx = market.get("sentiment") or {}
        if not isinstance(sentiment_ctx, dict):
            sentiment_ctx = {}

        items = sentiment_ctx.get("news") or sentiment_ctx.get("headlines") or []
        if not isinstance(items, list):
            items = []

        aggregate = _as_float(sentiment_ctx.get("aggregate_score"))
        social_buzz = _as_float(sentiment_ctx.get("social_buzz_ratio"))

        if not items and aggregate is None:
            return self.insufficient(
                f"No news, headline or sentiment data was supplied for {symbol}; "
                "the sentiment dimension is unavailable for this run.",
                data_quality=DataQuality.NONE,
            )

        deterministic = self._deterministic(symbol, items, aggregate, social_buzz)

        if deterministic.status == AgentStatus.SUCCESS:
            payload = {
                "aggregate_score": aggregate,
                "social_buzz_ratio": social_buzz,
                "headlines": [
                    {
                        "headline": i.get("headline") or i.get("title"),
                        "source": i.get("source"),
                        "score": i.get("sentiment_score"),
                    }
                    for i in items
                    if isinstance(i, dict)
                ][:12],
            }
            prompt = (
                f"Symbol: {symbol}\n"
                f"Sentiment data:\n{json.dumps(payload, indent=2)}\n\n"
                "Assess the prevailing market sentiment."
            )
            refined = await self.maybe_llm_refine(SYSTEM_PROMPT, prompt, deterministic)
            refined.evidence = deterministic.evidence
            return refined
        return deterministic

    # ------------------------------------------------------------------

    def _deterministic(
        self,
        symbol: str,
        items: list[Any],
        aggregate: Optional[float],
        social_buzz: Optional[float],
    ) -> AgentOutput:
        scores: list[float] = []
        evidence: list[Evidence] = []
        scored_headlines = 0

        for item in items:
            if not isinstance(item, dict):
                continue
            headline = str(item.get("headline") or item.get("title") or "").strip()
            if not headline:
                continue
            source = str(item.get("source") or "news feed").strip()

            explicit = _as_float(item.get("sentiment_score"))
            if explicit is not None:
                score = max(-1.0, min(1.0, explicit))
                scored_headlines += 1
            else:
                score = self._lexicon_score(headline)

            scores.append(score)
            evidence.append(
                Evidence(
                    source=source,
                    section=str(item.get("published_at") or "headline"),
                    text=headline,
                    score=round(score, 3),
                )
            )

        if aggregate is not None:
            scores.append(max(-1.0, min(1.0, aggregate)))

        if not scores:
            return self.insufficient(
                f"Sentiment items were supplied for {symbol} but none carried a usable "
                "headline or score.",
                data_quality=DataQuality.LOW,
                evidence=evidence,
            )

        mean = sum(scores) / len(scores)
        spread = max(scores) - min(scores) if len(scores) > 1 else 0.0

        if mean >= 0.15:
            signal = Signal.BULLISH
        elif mean <= -0.15:
            signal = Signal.BEARISH
        else:
            signal = Signal.NEUTRAL

        reasoning = [
            f"Aggregated {len(scores)} sentiment input(s) for {symbol}; "
            f"mean tone is {mean:+.2f} on a -1 to +1 scale."
        ]
        positives = [e for e in evidence if (e.score or 0) > 0.15]
        negatives = [e for e in evidence if (e.score or 0) < -0.15]
        if positives:
            reasoning.append(
                f"Positive coverage led by: \"{positives[0].text}\" ({positives[0].source})."
            )
        if negatives:
            reasoning.append(
                f"Countervailing coverage: \"{negatives[0].text}\" ({negatives[0].source})."
            )
        if spread > 1.0:
            reasoning.append(
                "Coverage is polarised, which makes the sentiment read less dependable."
            )
        if social_buzz is not None and social_buzz > 2.0:
            reasoning.append(
                f"Social chatter is {social_buzz:.1f}x baseline — elevated retail attention, "
                "which can amplify short-term moves in either direction."
            )

        quality = self._quality(len(evidence), scored_headlines, aggregate)
        confidence = min(0.85, 0.30 + abs(mean) * 0.55)
        if spread > 1.0:
            confidence *= 0.85
        if quality == DataQuality.MEDIUM:
            confidence *= 0.9
        elif quality == DataQuality.LOW:
            confidence *= 0.75

        return AgentOutput(
            agent=self.name,
            status=AgentStatus.SUCCESS,
            signal=signal,
            confidence=round(confidence, 3),
            reasoning=reasoning,
            evidence=evidence,
            data_quality=quality,
        )

    @staticmethod
    def _lexicon_score(headline: str) -> float:
        tokens = {t.strip(".,!?:;\"'()").lower() for t in headline.split()}
        pos = len(tokens & POSITIVE_WORDS)
        neg = len(tokens & NEGATIVE_WORDS)
        if pos == neg:
            return 0.0
        return max(-1.0, min(1.0, (pos - neg) / max(pos + neg, 1)))

    @staticmethod
    def _quality(
        headline_count: int, scored_headlines: int, aggregate: Optional[float]
    ) -> DataQuality:
        if headline_count == 0 and aggregate is None:
            return DataQuality.NONE
        if headline_count >= 4 and scored_headlines >= 2:
            return DataQuality.HIGH
        if headline_count >= 2 or aggregate is not None:
            return DataQuality.MEDIUM
        return DataQuality.LOW
