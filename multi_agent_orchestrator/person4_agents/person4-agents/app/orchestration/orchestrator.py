"""
Orchestrator.

Fetches context through adapters, runs the three agents CONCURRENTLY with
asyncio.gather, isolates failures, runs the deterministic risk engine, calls
synthesis, and records a structured reasoning trace the frontend can render
without knowing anything about agent internals.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Optional, Sequence

from app.adapters import (
    MarketSignalProvider,
    ProfileProvider,
    RAGProvider,
)
from app.agents.base_agent import BaseAgent
from app.agents.fundamental_agent import FundamentalAgent
from app.agents.sentiment_agent import SentimentAgent
from app.agents.technical_agent import TechnicalAgent
from app.config import Settings, settings as default_settings
from app.risk.risk_engine import RiskEngine
from app.schemas.models import (
    AgentOutput,
    AgentStatus,
    AnalysisResult,
    DataQuality,
    RiskAssessment,
    TraceEvent,
    UserProfile,
)
from app.synthesis.synthesizer import Synthesizer


class TraceRecorder:
    """Builds the ordered reasoning trace."""

    def __init__(self) -> None:
        self._events: list[TraceEvent] = []

    def add(self, stage: str, summary: str, detail: Optional[dict[str, Any]] = None) -> None:
        self._events.append(
            TraceEvent(
                step=len(self._events) + 1,
                stage=stage,
                summary=summary,
                detail=detail or {},
            )
        )

    @property
    def events(self) -> list[TraceEvent]:
        return list(self._events)


class Orchestrator:
    """Coordinates the agent fleet. Owns no data of its own."""

    def __init__(
        self,
        market_provider: Optional[MarketSignalProvider] = None,
        rag_provider: Optional[RAGProvider] = None,
        profile_provider: Optional[ProfileProvider] = None,
        agents: Optional[Sequence[BaseAgent]] = None,
        config: Optional[Settings] = None,
    ):
        self.settings = config or default_settings
        self.market_provider = market_provider
        self.rag_provider = rag_provider
        self.profile_provider = profile_provider
        self.agents: list[BaseAgent] = list(agents) if agents else [
            TechnicalAgent(),
            FundamentalAgent(),
            SentimentAgent(),
        ]
        self.risk_engine = RiskEngine()
        self.synthesizer = Synthesizer(config=self.settings)

    # ------------------------------------------------------------------

    async def run(
        self,
        symbol: str,
        market_data: Optional[dict[str, Any]] = None,
        rag_context: Optional[dict[str, Any]] = None,
        user_profile: Optional[dict[str, Any] | UserProfile] = None,
        query: str = "",
    ) -> AnalysisResult:
        started = time.perf_counter()
        symbol = (symbol or "UNKNOWN").strip().upper()
        trace = TraceRecorder()

        # -- 1. input received -----------------------------------------
        market_data, rag_context, profile, fetch_errors = await self._gather_inputs(
            symbol, market_data, rag_context, user_profile, query
        )

        trace.add(
            "input_received",
            f"Analysis requested for {symbol} on behalf of user "
            f"'{profile.user_id}' ({profile.risk_tolerance} risk tolerance).",
            {
                "symbol": symbol,
                "user_id": profile.user_id,
                "market_indicators_supplied": len((market_data.get("indicators") or {})),
                "rag_chunks_supplied": len(rag_context.get("chunks") or []),
                "input_errors": fetch_errors,
            },
        )

        context = {
            "market_data": market_data,
            "rag_context": rag_context,
            "sentiment_context": market_data.get("sentiment") or rag_context.get("sentiment") or {},
            "user_profile": profile.model_dump(),
        }

        # -- 2. agents started ------------------------------------------
        agent_names = [a.name for a in self.agents]
        trace.add(
            "agents_started",
            f"Dispatching {len(self.agents)} agents in parallel: {', '.join(agent_names)}.",
            {"agents": agent_names, "execution": "asyncio.gather (concurrent)"},
        )

        outputs = await self._run_agents_parallel(symbol, context)

        # -- 3/4/5. per-agent results -----------------------------------
        for output in outputs:
            trace.add(
                f"{output.agent}_result",
                self._describe_agent(output),
                {
                    "agent": output.agent,
                    "status": output.status.value,
                    "signal": output.signal.value,
                    "confidence": output.confidence,
                    "data_quality": output.data_quality.value,
                    "latency_ms": output.latency_ms,
                    "evidence_count": len(output.evidence),
                    "errors": output.errors,
                },
            )

        failed_agents = [
            o.agent for o in outputs if o.status in (AgentStatus.FAILED, AgentStatus.INSUFFICIENT_DATA)
        ]

        # -- risk assessment ---------------------------------------------
        interim_quality = self.synthesizer._overall_quality(outputs)
        risk: RiskAssessment = self.risk_engine.assess(
            symbol=symbol,
            profile=profile,
            market_data=market_data,
            data_quality=interim_quality,
        )

        # -- 6/7/8. synthesis --------------------------------------------
        outcome = self.synthesizer.synthesize(symbol, outputs, risk)

        trace.add(
            "conflict_resolution",
            (
                "Agent signals conflict; synthesis resolved the disagreement explicitly."
                if outcome.conflict["conflicted"]
                else "No directional conflict between agents; signals were combined directly."
            ),
            outcome.conflict | {"weighted_score": outcome.directional_score},
        )

        trace.add(
            "risk_adjustment",
            (
                f"Risk level {risk.risk_level.value} (score {risk.risk_score:.2f}) applied to the "
                f"market signal {outcome.final_signal.value}, producing recommendation "
                f"{outcome.recommendation.value}. The market signal itself was not altered."
            ),
            {
                "risk_level": risk.risk_level.value,
                "risk_score": risk.risk_score,
                "exposure_pct": risk.exposure_pct,
                "concentration_score": risk.concentration_score,
                "downgrade_steps": risk.downgrade_steps,
                "max_bullish_action": risk.max_bullish_action.value,
                "risk_factors": risk.risk_factors,
                "personalization": risk.personalization,
            },
        )

        total_latency = int((time.perf_counter() - started) * 1000)

        trace.add(
            "final_synthesis",
            (
                f"Final: {outcome.final_signal.value} with confidence "
                f"{outcome.confidence:.2f}; recommendation {outcome.recommendation.value} for "
                f"user '{profile.user_id}'. Data quality {outcome.data_quality.value}."
            ),
            {
                "final_signal": outcome.final_signal.value,
                "confidence": outcome.confidence,
                "recommendation": outcome.recommendation.value,
                "sources_cited": len(outcome.sources),
                "failed_agents": failed_agents,
                "total_latency_ms": total_latency,
            },
        )

        reasoning = list(outcome.reasoning)
        if fetch_errors:
            reasoning.append(
                "Input warnings: " + "; ".join(fetch_errors) + "."
            )

        return AnalysisResult(
            symbol=symbol,
            final_signal=outcome.final_signal,
            confidence=outcome.confidence,
            recommendation=outcome.recommendation,
            reasoning=reasoning,
            agent_outputs=outputs,
            sources=outcome.sources,
            risk_factors=risk.risk_factors,
            personalization=risk.personalization,
            data_quality=outcome.data_quality,
            failed_agents=failed_agents,
            reasoning_trace=trace.events,
            directional_score=outcome.directional_score,
            risk_level=risk.risk_level,
            user_id=profile.user_id,
            total_latency_ms=total_latency,
        )

    # ------------------------------------------------------------------

    async def _run_agents_parallel(
        self, symbol: str, context: dict[str, Any]
    ) -> list[AgentOutput]:
        """Concurrent execution. One agent's failure never sinks the others."""
        results = await asyncio.gather(
            *(agent.run(symbol, context) for agent in self.agents),
            return_exceptions=True,
        )

        outputs: list[AgentOutput] = []
        for agent, result in zip(self.agents, results):
            if isinstance(result, AgentOutput):
                outputs.append(result)
            elif isinstance(result, BaseException):
                # BaseAgent.run already contains exceptions; this is the
                # belt-and-braces path for anything truly unexpected.
                outputs.append(
                    agent.failure(f"unhandled {type(result).__name__}: {result}")
                )
            else:  # pragma: no cover - defensive
                outputs.append(agent.failure(f"invalid agent return type: {type(result).__name__}"))
        return outputs

    # ------------------------------------------------------------------

    async def _gather_inputs(
        self,
        symbol: str,
        market_data: Optional[dict[str, Any]],
        rag_context: Optional[dict[str, Any]],
        user_profile: Optional[dict[str, Any] | UserProfile],
        query: str,
    ) -> tuple[dict[str, Any], dict[str, Any], UserProfile, list[str]]:
        """Direct payloads win; providers are the fallback. Never raises."""
        errors: list[str] = []

        async def fetch(coro, label: str, fallback: Any):
            try:
                return await coro
            except Exception as exc:
                errors.append(f"{label} provider failed ({type(exc).__name__}: {exc})")
                return fallback

        tasks: dict[str, Any] = {}
        if market_data is None and self.market_provider is not None:
            tasks["market"] = fetch(
                self.market_provider.get_signals(symbol), "market", {}
            )
        if rag_context is None and self.rag_provider is not None:
            tasks["rag"] = fetch(
                self.rag_provider.retrieve(symbol, query or f"{symbol} outlook and risks"),
                "rag",
                {"chunks": []},
            )
        if user_profile is None and self.profile_provider is not None:
            tasks["profile"] = fetch(
                self.profile_provider.get_profile("demo_conservative"), "profile", {}
            )

        if tasks:
            fetched = dict(zip(tasks.keys(), await asyncio.gather(*tasks.values())))
        else:
            fetched = {}

        market = market_data if market_data is not None else fetched.get("market", {})
        rag = rag_context if rag_context is not None else fetched.get("rag", {"chunks": []})
        raw_profile = user_profile if user_profile is not None else fetched.get("profile", {})

        if not isinstance(market, dict):
            errors.append("market data was not a dict; ignoring it")
            market = {}
        if not isinstance(rag, dict):
            errors.append("rag context was not a dict; ignoring it")
            rag = {"chunks": []}

        if isinstance(raw_profile, UserProfile):
            profile = raw_profile
        else:
            try:
                profile = UserProfile(**(raw_profile or {}))
            except Exception as exc:
                errors.append(f"user profile could not be parsed ({type(exc).__name__}); using defaults")
                profile = UserProfile()

        if not market.get("indicators") and not any(
            k in market for k in ("price", "rsi_14", "momentum_20d_pct")
        ):
            errors.append("market data contained no usable indicators")
        if not rag.get("chunks"):
            errors.append("retrieval returned no document chunks")

        return market, rag, profile, errors

    # ------------------------------------------------------------------

    @staticmethod
    def _describe_agent(output: AgentOutput) -> str:
        if output.status == AgentStatus.FAILED:
            reason = output.errors[0] if output.errors else "unknown error"
            return (
                f"{output.agent.title()} agent FAILED ({reason}). Its view is excluded; "
                "remaining agents continue."
            )
        if output.status == AgentStatus.INSUFFICIENT_DATA:
            return (
                f"{output.agent.title()} agent returned insufficient_data and abstained "
                "rather than producing an unsupported view."
            )
        headline = output.reasoning[0] if output.reasoning else "no narrative supplied"
        return (
            f"{output.agent.title()} agent returned {output.signal.value} at confidence "
            f"{output.confidence:.2f} ({output.data_quality.value} data quality, "
            f"{output.latency_ms}ms). {headline}"
        )
