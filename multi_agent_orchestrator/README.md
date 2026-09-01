# Person 4 — Multi-Agent Reasoning, Risk & Synthesis Module

Part of **PS-01: Multi-Agent Autonomous Financial Intelligence System for Retail Investors**
(HACKVERSE Sprint 1, IEEE RAS · VIT Chennai).

---

## 1. What this module does

This is the reasoning core of the system. It takes market indicators, retrieved
documents and a user profile, runs three specialized agents **in parallel**,
resolves their disagreements, applies a deterministic risk layer, and returns a
single explainable recommendation with a full reasoning trace.

It owns:

1. Multi-agent orchestration
2. Technical Agent reasoning
3. Fundamental / RAG Agent reasoning
4. Sentiment Agent reasoning
5. Risk reasoning layer
6. Parallel execution
7. Structured agent contracts
8. Synthesis
9. Reasoning trace
10. Agent failure / degraded-data handling

It deliberately does **not** contain: a frontend, market data ingestion, a market
data API, a vector database, document ingestion, a user database, a portfolio
database, or a metrics dashboard. Those belong to other teammates and are
reached only through adapter interfaces.

Three properties matter most for the demo:

* **It never crashes on bad data.** Missing indicators, empty retrieval, a
  crashed agent and malformed payloads all degrade the result instead of raising.
* **It never fabricates a citation.** If retrieval returns nothing, the
  Fundamental Agent returns `insufficient_data` and says why.
* **It is personalized.** Identical market input produces a different
  recommendation for a conservative user than for an aggressive one — while the
  underlying market signal stays the same.

---

## 2. Architecture

```
 Market Data ──▶ MarketSignalProvider ┐
 Doc Corpus  ──▶ RAGProvider          ├──▶  ORCHESTRATOR
 User Profile ─▶ ProfileProvider      ┘          │
                                                 │  asyncio.gather
                            ┌────────────────────┼────────────────────┐
                            ▼                    ▼                    ▼
                    Technical Agent      Fundamental Agent     Sentiment Agent
                    (interprets          (RAG-grounded,        (news / headline
                     indicators)          cites sources)        aggregation)
                            └────────────────────┼────────────────────┘
                                                 ▼
                                          RISK ENGINE  (deterministic, no LLM)
                                                 ▼
                                            SYNTHESIS
                                    weighted score → conflict
                                    resolution → confidence
                                                 ▼
                                     Personalized AnalysisResult
                                       + 8-step reasoning trace
```

**Decision flow**

1. Inputs arrive directly or are fetched concurrently through adapters.
2. All three agents run at once. A failure in one is contained and the others
   proceed.
3. The risk engine scores the user's portfolio and behaviour deterministically.
4. Synthesis computes a weighted directional score from agent evidence **only**.
5. Risk constrains the *recommendation* derived from that signal. It never
   rewrites the signal itself.
6. Every step is appended to a structured trace the frontend can render.

**Why the risk layer is deterministic:** an LLM that can silently flip a
recommendation is not auditable. Risk here is arithmetic on the user's declared
limits, so the demo can always explain exactly why a BUY became a HOLD.

---

## 3. Folder structure

```
person4-agents/
├── app/
│   ├── agents/
│   │   ├── base_agent.py          # lifecycle, timing, timeout, failure containment
│   │   ├── technical_agent.py     # interprets supplied indicators
│   │   ├── fundamental_agent.py   # RAG-grounded, strict citation discipline
│   │   └── sentiment_agent.py     # news / headline aggregation
│   ├── orchestration/
│   │   └── orchestrator.py        # parallel execution + reasoning trace
│   ├── synthesis/
│   │   └── synthesizer.py         # weighted score, conflict resolution, confidence
│   ├── risk/
│   │   └── risk_engine.py         # deterministic risk + personalization
│   ├── schemas/
│   │   └── models.py              # every cross-boundary contract
│   ├── adapters/
│   │   ├── market_adapter.py      # MarketSignalProvider protocol + mocks
│   │   ├── rag_adapter.py         # RAGProvider protocol + mocks
│   │   └── profile_adapter.py     # ProfileProvider protocol + mocks
│   ├── api.py                     # analyze() / analyze_sync()  ← public surface
│   ├── llm.py                     # optional Anthropic wrapper
│   └── config.py                  # weights, bands, caps, timeouts
├── mocks/
│   ├── market_data.json           # RELIANCE + degraded + bearish-news variants
│   ├── rag_response.json          # normal / empty / bearish / irrelevant
│   └── user_profile.json          # demo_conservative + demo_aggressive
├── tests/                         # 73 tests
├── conftest.py                    # makes `app` importable
├── pytest.ini
├── requirements.txt
├── .env.example
├── integration_example.py
└── README.md
```

---

## 4. Installation

Python 3.11+ (developed and tested on 3.12).

```bash
cd person4-agents
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

That is the whole setup. No database, no broker, no vector store, no external
service is required to run this module or its tests.

---

## 5. Environment variables

Every variable is optional — copy `.env.example` to `.env` only if you want to
change defaults.

| Variable | Default | Purpose |
|---|---|---|
| `USE_LLM` | `false` | `true` adds Claude-generated narrative reasoning |
| `ANTHROPIC_API_KEY` | *(empty)* | Required only when `USE_LLM=true` |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-5` | Model string for the SDK |
| `LLM_TIMEOUT_S` | `20` | Per-call LLM timeout |
| `AGENT_TIMEOUT_S` | `25` | Per-agent hard timeout |
| `WEIGHT_TECHNICAL` | `0.35` | Technical weight in synthesis |
| `WEIGHT_FUNDAMENTAL` | `0.40` | Fundamental weight in synthesis |
| `WEIGHT_SENTIMENT` | `0.25` | Sentiment weight in synthesis |
| `STRONG_BAND` | `0.50` | Score threshold for BULLISH / BEARISH |
| `MODERATE_BAND` | `0.15` | Score threshold for the MODERATELY_* bands |
| `CONFLICT_PENALTY` | `0.30` | Confidence reduction when agents disagree |
| `MISSING_AGENT_CAP` | `0.65` | Confidence ceiling when an agent is unavailable |
| `LOW_QUALITY_CAP` | `0.50` | Confidence ceiling on low-quality data |
| `NO_EVIDENCE_CAP` | `0.55` | Confidence ceiling when nothing was cited |

**On the LLM:** with `USE_LLM=false` the agents use deterministic rule-based
reasoning and the module works completely offline. With `USE_LLM=true` each agent
also asks Claude for narrative reasoning, and the LLM may adjust the signal — but
only within ±0.20 of the deterministic confidence, so a hallucinated 0.99 cannot
hijack synthesis. Any error, timeout or malformed JSON silently falls back to the
deterministic result. **The demo cannot break because of the LLM.**

---

## 6. How to run

```bash
python integration_example.py
```

This prints five scenarios end to end: happy path (conservative), the same
market data for an aggressive user, and degraded scenarios A, B and C.

In your own code:

```python
import asyncio
from app import analyze

result = asyncio.run(analyze(
    symbol="RELIANCE",
    market_data=market_data,      # from the signal engine
    rag_context=rag_context,      # from the vector store
    user_profile=user_profile,    # from the profile service
))

print(result.final_signal.value, result.recommendation.value, result.confidence)
payload = result.to_frontend_dict()   # plain JSON for the API layer
```

---

## 7. How to run tests

```bash
pytest              # 73 tests, ~1 second, no network required
pytest -v           # verbose
pytest tests/test_parallel_execution.py -v    # the concurrency proof
```

Coverage by requirement:

| # | Area | File |
|---|---|---|
| 1 | Technical agent | `tests/test_agents.py` |
| 2 | Fundamental agent | `tests/test_agents.py` |
| 3 | Sentiment agent | `tests/test_agents.py` |
| 4 | Parallel execution | `tests/test_parallel_execution.py` |
| 5 | Synthesis | `tests/test_synthesis.py` |
| 6 | Conflicting signals | `tests/test_synthesis.py` |
| 7 | Missing RAG evidence | `tests/test_degraded_data.py` |
| 8 | Failed agent | `tests/test_degraded_data.py` |
| 9 | Risk calculation | `tests/test_risk_and_profiles.py` |
| 10 | Different user profiles | `tests/test_risk_and_profiles.py` |
| 11 | Full end-to-end | `tests/test_end_to_end.py` |

The parallel test proves concurrency two ways: three agents that each sleep
0.30 s finish in well under the 0.90 s a sequential run would take, and every
agent's start timestamp precedes the earliest end timestamp.

---

## 8. Input contracts

All three inputs are plain dicts. Missing keys degrade quality; they do not crash.

**`market_data`** — from the signal engine:

```json
{
  "symbol": "RELIANCE",
  "as_of": "2026-02-13T15:30:00+05:30",
  "price": 1412.30,
  "feed_status": "ok",
  "indicators": {
    "rsi_14": 61.4,
    "momentum_5d_pct": 3.2,
    "momentum_20d_pct": 7.8,
    "volume_ratio_20d": 1.86,
    "sma_20": 1380.40,
    "sma_50": 1341.15,
    "sma_200": 1288.70,
    "macd_histogram": 4.62,
    "atr_pct": 1.8,
    "volatility_30d_pct": 21.6
  },
  "risk_flags": [],
  "sentiment": {
    "aggregate_score": 0.34,
    "social_buzz_ratio": 2.4,
    "news": [
      {
        "headline": "Reliance Jio adds record subscribers …",
        "source": "Economic Times",
        "published_at": "2026-02-12T09:14:00+05:30",
        "sentiment_score": 0.72
      }
    ]
  }
}
```

Every indicator is optional. `feed_status` of `stale` / `degraded` / `partial`
lowers data quality. `sentiment_score` is optional — a keyword lexicon is used
when it is absent. Sentiment may also be passed separately as
`sentiment_context`.

**`rag_context`** — from the vector store:

```json
{
  "query": "RELIANCE Q3 FY26 results, risks and outlook",
  "retrieval_status": "ok",
  "chunks": [
    {
      "source": "RELIANCE_Q3FY26_earnings_call_transcript.pdf",
      "section": "Management Commentary",
      "text": "Consolidated EBITDA for the quarter grew 11.4% …",
      "score": 0.93
    }
  ]
}
```

`chunks: []` is valid and expected — see §13. A chunk missing `source` or `text`
is dropped, because it cannot be cited.

**`user_profile`** — from the profile service:

```json
{
  "user_id": "demo_conservative",
  "risk_tolerance": "conservative",
  "investment_horizon": "long",
  "experience_level": "beginner",
  "max_position_pct": 8.0,
  "concentration_score": 0.71,
  "cash_pct": 4.0,
  "holdings": [{ "symbol": "RELIANCE", "weight_pct": 22.0 }],
  "behavioral_flags": ["panic_seller"]
}
```

`risk_tolerance` ∈ `conservative | moderate | aggressive`. `concentration_score`
is derived from `holdings` if omitted. Unknown extra keys are preserved.

---

## 9. Output contracts

**Agent output** — every agent returns exactly this, success or failure:

```json
{
  "agent": "technical",
  "status": "success",
  "signal": "BULLISH",
  "confidence": 0.88,
  "reasoning": ["20-day price momentum is +7.8% …"],
  "evidence": [{ "source": "…", "section": "…", "text": "…", "score": 0.93 }],
  "data_quality": "HIGH",
  "latency_ms": 820,
  "errors": []
}
```

`signal` ∈ `BULLISH | NEUTRAL | BEARISH`
`status` ∈ `success | insufficient_data | failed`
`data_quality` ∈ `HIGH | MEDIUM | LOW | NONE`

**Final output** — `AnalysisResult`, JSON via `.to_frontend_dict()`:

```json
{
  "symbol": "RELIANCE",
  "final_signal": "BULLISH",
  "confidence": 0.72,
  "recommendation": "HOLD",
  "reasoning": ["Weighted directional score …", "Risk level CRITICAL moved …"],
  "agent_outputs": [ … ],
  "sources": [ … ],
  "risk_factors": ["Position limit breached: RELIANCE is 22.0% …"],
  "personalization": ["Risk tolerance on file: conservative.", …],
  "data_quality": "HIGH",
  "failed_agents": [],
  "reasoning_trace": [ … ],

  "directional_score": 0.624,
  "risk_level": "CRITICAL",
  "user_id": "demo_conservative",
  "total_latency_ms": 2,
  "generated_at": "2026-02-13T10:00:00+00:00"
}
```

`final_signal` ∈ `BULLISH | MODERATELY_BULLISH | NEUTRAL | MODERATELY_BEARISH | BEARISH`
`recommendation` ∈ `BUY | ACCUMULATE | HOLD | REDUCE | SELL`
`risk_level` ∈ `LOW | MODERATE | HIGH | CRITICAL`

**Reasoning trace** — always exactly these eight steps, in order:

| step | stage |
|---|---|
| 1 | `input_received` |
| 2 | `agents_started` |
| 3 | `technical_result` |
| 4 | `fundamental_result` |
| 5 | `sentiment_result` |
| 6 | `conflict_resolution` |
| 7 | `risk_adjustment` |
| 8 | `final_synthesis` |

Each event is `{step, stage, summary, detail, timestamp}`. **The frontend only
needs `step`, `stage` and `summary`** — `summary` is a complete human-readable
sentence. `detail` holds structured extras for expandable views.

### How the numbers are produced

*Directional score* = Σ(weight × confidence × direction) ÷ Σ(weight), over
**participating** agents only, where BULLISH = +1, NEUTRAL = 0, BEARISH = −1.
Because the denominator counts only agents that produced a usable view, the score
stays comparable when an agent drops out — the loss of coverage is expressed in
`confidence`, not by silently dragging the score toward zero.

*Confidence* starts as the quality-weighted mean of agent confidences, then:
scaled by coverage (missing agents shrink it), reduced when agents conflict,
raised 15% when they unanimously agree, and finally hard-capped by the
`MISSING_AGENT_CAP` / `LOW_QUALITY_CAP` / `NO_EVIDENCE_CAP` rules. It cannot
exceed 0.95.

*Recommendation* comes from the signal band, then risk moves it **down** the
ladder `SELL → REDUCE → HOLD → ACCUMULATE → BUY` only. Risk can never make advice
more aggressive, never push a bullish signal below HOLD, and never alters
`final_signal`. Confidence below 0.35 also forces HOLD.

---

## 10. Mock usage

```python
from app.adapters import MockMarketSignalProvider, MockRAGProvider, MockProfileProvider

market  = await MockMarketSignalProvider().get_signals("RELIANCE")
rag     = await MockRAGProvider().retrieve("RELIANCE")
profile = await MockProfileProvider().get_profile("demo_aggressive")
```

Available keys:

| File | Keys |
|---|---|
| `market_data.json` | `RELIANCE`, `RELIANCE_DEGRADED` (partial feed), `RELIANCE_BEARISH_NEWS` |
| `rag_response.json` | `RELIANCE`, `RELIANCE_EMPTY`, `RELIANCE_BEARISH`, `RELIANCE_IRRELEVANT` |
| `user_profile.json` | `demo_conservative`, `demo_aggressive` |

`EmptyRAGProvider` is a ready-made degraded-scenario provider that always returns
zero chunks.

**The headline demo:** `RELIANCE` market data + `RELIANCE` retrieval gives
BULLISH at 0.72 confidence for both users — but `demo_conservative` is told to
**HOLD** (22% existing exposure against an 8% self-declared cap, high
concentration, thin cash, panic-selling history → CRITICAL risk) while
`demo_aggressive` is told to **BUY** (4% exposure, diversified, 18% cash → LOW
risk). Same data, same signal, different advice.

Pairing `RELIANCE_BEARISH_NEWS` with `RELIANCE_BEARISH` retrieval demonstrates
scenario D: technical and sentiment read bullish, the filings read bearish, and
synthesis names the conflict explicitly.

---

## 11. Adapter interfaces

This module never imports a teammate's implementation. Anything external is
reached through one of three `typing.Protocol` interfaces — implement the method
and pass the object in. No inheritance or registration needed.

```python
class MarketSignalProvider(Protocol):
    async def get_signals(self, symbol: str) -> dict: ...

class RAGProvider(Protocol):
    async def retrieve(self, symbol: str, query: str = "", k: int = 6) -> dict: ...

class ProfileProvider(Protocol):
    async def get_profile(self, user_id: str) -> dict: ...
```

```python
from app import analyze

result = await analyze(
    "RELIANCE",
    market_provider=YourSignalEngineAdapter(),
    rag_provider=YourVectorStoreAdapter(),
    profile_provider=YourProfileServiceAdapter(),
)
```

Direct payloads take precedence; providers are used only for arguments left as
`None`, and provider calls run concurrently. **A provider that raises is caught**
— the error is recorded in `reasoning` and the pipeline continues.

---

## 12. Integration example

`integration_example.py` is runnable and covers every scenario a judge will ask
about. The minimum a caller needs:

```python
import asyncio
from app import analyze

async def main():
    result = await analyze("RELIANCE", market_data, rag_context, user_profile)
    return result.to_frontend_dict()

asyncio.run(main())
```

For non-async callers (a Flask route, a script):

```python
from app import analyze_sync
result = analyze_sync("RELIANCE", market_data, rag_context, user_profile)
```

`analyze_sync` raises if called from inside a running event loop — use
`await analyze(...)` there (FastAPI, aiohttp).

---

## 13. Failure / degraded-data behaviour

The pipeline never raises for data problems and never emits an uncited claim.

| Scenario | Behaviour |
|---|---|
| **A — an agent fails or hangs** | Caught by `BaseAgent.run` (with a hard timeout). That agent returns `status: failed`, confidence 0, and its name appears in `failed_agents`. Other agents are unaffected; synthesis proceeds on the survivors with confidence capped at 0.65. |
| **B — RAG returns no documents** | The Fundamental Agent returns `insufficient_data`, confidence 0.0, `evidence: []`, and states that no filing was retrieved. **No citation is ever invented.** Its 0.40 weight leaves the calculation and confidence is capped. |
| **C — incomplete market data** | Present indicators are used; `data_quality` drops to MEDIUM or LOW. Fewer than two usable indicators gives `insufficient_data`. Degraded data is itself scored as a risk factor. |
| **D — agents disagree** | Synthesis names the conflict, reports the weighted mass of each side, identifies the strongest single input and whether it is backed by citations, and reduces confidence proportionally to the disagreement. |
| Retrieved chunks are irrelevant | `insufficient_data` rather than a manufactured direction. |
| A provider raises | Caught in `_gather_inputs`; recorded as an input warning; the run continues. |
| Malformed / `None` payloads | Coerced or ignored; the run still returns a valid `AnalysisResult`. |
| Every agent fails | NEUTRAL, confidence 0.0, HOLD, `data_quality: NONE`, empty `sources`, full 8-step trace intact. |

Confidence is never allowed to look better than the data justifies: missing
agents cap it at 0.65, low-quality data at 0.50, and a run with no citations at
0.55.

---

## 14. Notes for Person 5 (integration)

**The whole public surface is two functions.**

```python
from app import analyze          # async — use this
from app import analyze_sync     # blocking wrapper for non-async callers
```

Do not import from `app.agents`, `app.synthesis` or `app.orchestration` — those
are internal and may change. `app.schemas.models` is stable and safe to import
for type hints.

**Wiring it up**

1. Pass raw dicts (simplest), or implement the three adapter protocols in §11.
2. Send `result.to_frontend_dict()` straight to the frontend — it is plain
   JSON-safe types with enums already flattened to strings.
3. Render `reasoning_trace` in order using `stage` and `summary`. No knowledge of
   agent internals is needed.
4. Surface `sources` for the attribution requirement, and `personalization` +
   `risk_factors` for the profiling requirement.

**Things worth knowing**

* `analyze()` does not raise for data problems. Check `failed_agents` and
  `data_quality` to decide what to show, not `try/except`.
* It is **stateless** — no database, no globals, no caching. Safe to call
  concurrently for many users; `asyncio.gather` over symbols works fine.
* Latency is a few milliseconds with `USE_LLM=false`, and a few seconds with
  `USE_LLM=true` (three parallel LLM calls, bounded by `LLM_TIMEOUT_S`).
  `total_latency_ms` and per-agent `latency_ms` are populated for the metrics
  dashboard.
* Leave `USE_LLM=false` for the live demo unless the API key is confirmed
  working. Nothing else changes.
* If the frontend needs a "why did this change?" view, `reasoning_trace[6]`
  (`risk_adjustment`) contains the exposure, concentration and downgrade detail
  that turned the market signal into the recommendation.
* Weights, bands and caps are all environment-tunable (§5) — no code change is
  needed to adjust the demo's behaviour.
