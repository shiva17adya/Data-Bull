"""
Fundamental Agent (RAG-grounded).

Hard rule: every fundamental claim must trace back to a retrieved chunk. If
retrieval comes back empty, this agent returns `insufficient_data` with an
explicit explanation. It never writes a citation it did not receive.
"""

from __future__ import annotations

import json
from typing import Any

from app.agents.base_agent import BaseAgent
from app.schemas.models import AgentOutput, AgentStatus, DataQuality, Evidence, Signal

POSITIVE_TERMS = {
    "growth": 1.0,
    "grew": 1.0,
    "increase": 0.9,
    "increased": 0.9,
    "rose": 0.9,
    "expansion": 1.0,
    "expanded": 1.0,
    "record": 1.0,
    "outperform": 1.2,
    "beat": 1.0,
    "improved": 0.9,
    "improvement": 0.9,
    "margin expansion": 1.4,
    "deleveraging": 1.0,
    "strong": 0.8,
    "robust": 0.9,
    "upgrade": 1.1,
    "surplus": 0.7,
    "free cash flow": 0.8,
    "capacity addition": 0.8,
    "order book": 0.7,
}

NEGATIVE_TERMS = {
    "decline": 1.0,
    "declined": 1.0,
    "fell": 0.9,
    "contraction": 1.1,
    "loss": 1.0,
    "impairment": 1.2,
    "litigation": 1.1,
    "penalty": 1.2,
    "investigation": 1.2,
    "show cause": 1.3,
    "downgrade": 1.2,
    "weak": 0.8,
    "weakness": 0.9,
    "headwind": 0.9,
    "margin pressure": 1.4,
    "debt increased": 1.2,
    "delay": 0.8,
    "shortfall": 1.0,
    "default": 1.4,
    "regulatory action": 1.3,
    "guidance cut": 1.4,
}

SYSTEM_PROMPT = (
    "You are a fundamental research agent inside a multi-agent investment system. "
    "You may ONLY use the retrieved excerpts provided. Never state a fact that is not in them. "
    "If the excerpts do not support a view, say so and choose NEUTRAL. "
    "Respond with ONLY a JSON object: "
    '{"signal": "BULLISH|NEUTRAL|BEARISH", "confidence": 0.0-1.0, "reasoning": ["...", "..."]}. '
    "Every reasoning string must reference the source filename it came from."
)


class FundamentalAgent(BaseAgent):
    name = "fundamental"

    async def analyze(self, symbol: str, context: dict[str, Any]) -> AgentOutput:
        rag = context.get("rag_context") or {}
        if not isinstance(rag, dict):
            rag = {}

        raw_chunks = rag.get("chunks")
        if raw_chunks is None:
            raw_chunks = rag.get("results") or rag.get("documents") or []
        if not isinstance(raw_chunks, list):
            raw_chunks = []

        evidence = self._to_evidence(raw_chunks)
        retrieval_status = str(rag.get("retrieval_status", "ok")).lower()

        # --- Scenario B: nothing retrieved -----------------------------
        if not evidence:
            reason = (
                f"No relevant filings or transcripts were retrieved for {symbol}"
                f"{' (retrieval status: ' + retrieval_status + ')' if retrieval_status != 'ok' else ''}. "
                "No fundamental claim can be made without source evidence, so this agent "
                "abstains rather than guessing."
            )
            output = self.insufficient(reason, data_quality=DataQuality.NONE)
            output.confidence = 0.0
            return output

        deterministic = self._deterministic(symbol, evidence, retrieval_status)

        if deterministic.status == AgentStatus.SUCCESS:
            excerpts = [
                {"source": e.source, "section": e.section, "text": e.text[:600]}
                for e in evidence
            ]
            prompt = (
                f"Symbol: {symbol}\n"
                f"Retrieved excerpts (the ONLY facts you may use):\n"
                f"{json.dumps(excerpts, indent=2)}\n\n"
                "Assess the fundamental picture strictly from these excerpts."
            )
            refined = await self.maybe_llm_refine(SYSTEM_PROMPT, prompt, deterministic)
            refined.evidence = evidence  # citations always come from retrieval
            return refined
        return deterministic

    # ------------------------------------------------------------------

    @staticmethod
    def _to_evidence(raw_chunks: list[Any]) -> list[Evidence]:
        evidence: list[Evidence] = []
        for chunk in raw_chunks:
            if not isinstance(chunk, dict):
                continue
            text = str(chunk.get("text") or chunk.get("content") or "").strip()
            source = str(chunk.get("source") or chunk.get("document") or "").strip()
            if not text or not source:
                # A chunk with no text or no attribution cannot be cited.
                continue
            score = chunk.get("score")
            try:
                score = float(score) if score is not None else None
            except (TypeError, ValueError):
                score = None
            evidence.append(
                Evidence(
                    source=source,
                    section=str(chunk.get("section") or chunk.get("heading") or "").strip(),
                    text=text,
                    score=score,
                )
            )
        return evidence

    def _deterministic(
        self,
        symbol: str,
        evidence: list[Evidence],
        retrieval_status: str,
    ) -> AgentOutput:
        total = 0.0
        matched_chunks = 0
        reasoning: list[str] = []

        for item in evidence:
            lowered = item.text.lower()
            pos = sum(w for term, w in POSITIVE_TERMS.items() if term in lowered)
            neg = sum(w for term, w in NEGATIVE_TERMS.items() if term in lowered)
            if pos == 0 and neg == 0:
                continue
            matched_chunks += 1
            relevance = item.score if item.score is not None else 0.7
            chunk_score = (pos - neg) / max(pos + neg, 1.0)
            total += chunk_score * relevance

            label = "supportive" if chunk_score > 0.1 else (
                "cautionary" if chunk_score < -0.1 else "mixed"
            )
            where = f"{item.source}" + (f" — {item.section}" if item.section else "")
            reasoning.append(
                f"{where}: {label} evidence — \"{self._snippet(item.text)}\""
            )

        if matched_chunks == 0:
            output = self.insufficient(
                f"{len(evidence)} document chunk(s) were retrieved for {symbol}, but none "
                "contained assessable fundamental commentary. Reporting neutral without "
                "inferring a direction.",
                data_quality=DataQuality.LOW,
                evidence=evidence,
            )
            output.confidence = 0.12
            return output

        normalized = max(-1.0, min(1.0, total / matched_chunks))

        if normalized >= 0.20:
            signal = Signal.BULLISH
        elif normalized <= -0.20:
            signal = Signal.BEARISH
        else:
            signal = Signal.NEUTRAL

        quality = self._quality(len(evidence), matched_chunks, evidence, retrieval_status)
        confidence = min(0.90, 0.30 + abs(normalized) * 0.55)
        if quality == DataQuality.MEDIUM:
            confidence *= 0.88
        elif quality == DataQuality.LOW:
            confidence *= 0.7

        reasoning.insert(
            0,
            f"Assessment grounded in {matched_chunks} of {len(evidence)} retrieved excerpt(s) "
            f"for {symbol}; all claims below are attributable to those sources.",
        )

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
    def _snippet(text: str, limit: int = 160) -> str:
        collapsed = " ".join(text.split())
        return collapsed if len(collapsed) <= limit else collapsed[: limit - 1] + "…"

    @staticmethod
    def _quality(
        retrieved: int,
        matched: int,
        evidence: list[Evidence],
        retrieval_status: str,
    ) -> DataQuality:
        if retrieved == 0:
            return DataQuality.NONE
        scores = [e.score for e in evidence if e.score is not None]
        avg_score = sum(scores) / len(scores) if scores else 0.7
        if retrieval_status in {"degraded", "partial", "stale"}:
            return DataQuality.LOW
        if retrieved >= 3 and matched >= 2 and avg_score >= 0.7:
            return DataQuality.HIGH
        if matched >= 2 or avg_score >= 0.6:
            return DataQuality.MEDIUM
        return DataQuality.LOW
