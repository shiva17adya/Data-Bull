"""
Base class for every specialized agent.

The important guarantee: `run()` *always* returns a valid `AgentOutput`. It
never raises. A crashed agent becomes a `failed` output with zero confidence
so the orchestrator can keep going with whatever survived.
"""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Any, Optional

from app.config import settings
from app.schemas.models import (
    AgentOutput,
    AgentStatus,
    DataQuality,
    Signal,
)


class BaseAgent(ABC):
    """All agents share the same lifecycle: analyze -> structured output."""

    name: str = "base"

    def __init__(self, timeout_s: Optional[float] = None):
        self.timeout_s = timeout_s if timeout_s is not None else settings.agent_timeout_s

    # -- to implement -----------------------------------------------------

    @abstractmethod
    async def analyze(self, symbol: str, context: dict[str, Any]) -> AgentOutput:
        """Produce the agent's view. May raise; `run()` contains it."""

    # -- lifecycle --------------------------------------------------------

    async def run(self, symbol: str, context: dict[str, Any]) -> AgentOutput:
        started = time.perf_counter()
        try:
            output = await asyncio.wait_for(
                self.analyze(symbol, context or {}), timeout=self.timeout_s
            )
            if not isinstance(output, AgentOutput):  # defensive
                raise TypeError(f"{self.name} agent returned {type(output).__name__}")
            output.agent = self.name
            output.latency_ms = self._elapsed_ms(started)
            return output
        except asyncio.TimeoutError:
            return self.failure(
                f"timed out after {self.timeout_s:.1f}s",
                latency_ms=self._elapsed_ms(started),
            )
        except asyncio.CancelledError:  # pragma: no cover - cooperative cancel
            raise
        except Exception as exc:
            return self.failure(
                f"{type(exc).__name__}: {exc}",
                latency_ms=self._elapsed_ms(started),
            )

    # -- helpers ----------------------------------------------------------

    @staticmethod
    def _elapsed_ms(started: float) -> int:
        return int((time.perf_counter() - started) * 1000)

    def failure(self, error: str, latency_ms: int = 0) -> AgentOutput:
        return AgentOutput(
            agent=self.name,
            status=AgentStatus.FAILED,
            signal=Signal.NEUTRAL,
            confidence=0.0,
            reasoning=[f"{self.name} agent could not complete its analysis."],
            evidence=[],
            data_quality=DataQuality.NONE,
            latency_ms=latency_ms,
            errors=[error],
        )

    def insufficient(
        self,
        reason: str,
        *,
        data_quality: DataQuality = DataQuality.LOW,
        evidence: Optional[list] = None,
    ) -> AgentOutput:
        return AgentOutput(
            agent=self.name,
            status=AgentStatus.INSUFFICIENT_DATA,
            signal=Signal.NEUTRAL,
            confidence=0.15,
            reasoning=[reason],
            evidence=evidence or [],
            data_quality=data_quality,
            errors=[],
        )

    async def maybe_llm_refine(
        self,
        system: str,
        prompt: str,
        deterministic: AgentOutput,
    ) -> AgentOutput:
        """Optionally let the LLM rewrite reasoning / adjust the signal.

        Falls back silently to the deterministic output. The LLM can only
        move confidence within a bounded range so a hallucinated 0.99 cannot
        hijack the synthesis.
        """
        from app.llm import structured_completion

        parsed = await structured_completion(system, prompt)
        if not parsed:
            return deterministic

        try:
            signal_raw = str(parsed.get("signal", deterministic.signal.value)).upper()
            signal = Signal(signal_raw) if signal_raw in Signal.__members__ else deterministic.signal

            conf_raw = parsed.get("confidence", deterministic.confidence)
            confidence = float(conf_raw)
            confidence = max(0.0, min(1.0, confidence))
            # Trust the deterministic estimate as an anchor: allow +/- 0.2.
            low = max(0.0, deterministic.confidence - 0.2)
            high = min(1.0, deterministic.confidence + 0.2)
            confidence = max(low, min(high, confidence))

            reasoning = parsed.get("reasoning", [])
            if isinstance(reasoning, str):
                reasoning = [reasoning]
            reasoning = [str(r).strip() for r in reasoning if str(r).strip()][:6]
            if not reasoning:
                reasoning = deterministic.reasoning

            deterministic.signal = signal
            deterministic.confidence = round(confidence, 3)
            deterministic.reasoning = reasoning
            return deterministic
        except (TypeError, ValueError):
            return deterministic
