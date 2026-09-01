# MEMBER5_FRONTEND_CONTRACT.md

**Derived from:** `MEMBER5_INTEGRATION_AUDIT.md` + direct inspection of Member 1–4 source.
**Scope:** Contract only. No teammate module is modified. No frontend or adapter code is written here.

---

# 1. Frontend Data Requirements

Every field the frontend needs, its type, its source module, and whether it can be guaranteed present.

| Field | Type | Source module | Required? |
|---|---|---|---|
| Stock/watchlist symbol | `string` | Member 1 `/symbols` (list of valid tickers) | Required |
| Current price | `float` | Member 1 `signals.market_data.price` | Optional (`null` if `data_status != OK`) |
| OHLCV | `{open, high, low, close, volume}` | Member 1 `signals.market_data` | Optional (`null` when unavailable) |
| Currency | `string` | Member 1 `signals.market_data.currency` | Optional |
| Overall market signal | `enum BULLISH\|NEUTRAL\|BEARISH` | Member 1 `overall_signal` | Required (never `UNAVAILABLE` per Member 1's own contract guarantee) |
| Overall market confidence | `float 0–1` | Member 1 `confidence` | Required |
| Signal dimensions (momentum/volume/RSI) | `{signal, value, confidence, evidence[]}` × 3 | Member 1 `signals.price_momentum/volume_anomaly/rsi` | Required keys always present; each dimension's `signal` may individually be `UNAVAILABLE` |
| Market data status | `enum OK\|DEGRADED\|UNAVAILABLE` | Member 1 `data_status` | Required |
| Market warnings | `string[]` | Member 1 `warnings` | Optional (may be empty) |
| Technical Agent output | `{status, signal, confidence, reasoning[], evidence[], data_quality, latency_ms, errors[]}` | Member 4 `agent_outputs[agent="technical"]` | Required key present; `status` may be `insufficient_data`/`failed` |
| Fundamental Agent output | same shape as above | Member 4 `agent_outputs[agent="fundamental"]` | Required key present; degrades same way |
| Sentiment Agent output | same shape as above | Member 4 `agent_outputs[agent="sentiment"]` | Required key present; **no real sentiment data source exists in this project** (see §12), so expect `insufficient_data` by default |
| Risk Agent output | **No standalone "risk agent" object exists.** Risk is expressed as `risk_level` + `risk_factors[]` inside the synthesis result | Member 4 `AnalysisResult.risk_level`, `.risk_factors` | Required (always populated, even if empty list) |
| Synthesis: final signal | `enum BULLISH\|MODERATELY_BULLISH\|NEUTRAL\|MODERATELY_BEARISH\|BEARISH` | Member 4 `AnalysisResult.final_signal` | Required |
| Synthesis: confidence | `float 0–1` | Member 4 `AnalysisResult.confidence` | Required |
| Synthesis: recommendation | `enum BUY\|ACCUMULATE\|HOLD\|REDUCE\|SELL` | Member 4 `AnalysisResult.recommendation` | Required |
| Synthesis: directional score | `float` | Member 4 `AnalysisResult.directional_score` | Required |
| Synthesis: reasoning | `string[]` | Member 4 `AnalysisResult.reasoning` | Required (may be short) |
| User profile: risk tolerance | `enum conservative\|moderate\|aggressive` | Member 3 `personalization.profile.risk_tolerance` | Required if `user_id` supplied, else omitted |
| User profile: investment horizon | `int` (years) | Member 3 `personalization.profile.investment_horizon_years` | Required if `user_id` supplied |
| Portfolio: total value | `float` | Member 3 `/portfolio.total_value` | Optional (0 if no holdings) |
| Portfolio: holdings | `[{symbol, quantity, average_price, current_price, value, position_percentage}]` | Member 3 `/portfolio.holdings` | Optional (empty array valid) |
| Portfolio concentration level | `enum none\|low\|moderate\|elevated\|high` | Member 3 `/portfolio/risk.concentration_level` or `personalization.portfolio_context.concentration_level` | Required if `user_id` supplied |
| Portfolio risk flags | `string[]` | Member 3 `/portfolio/risk.risk_flags` | Optional (may be empty) |
| Personalization factors | `string[]` | Member 3 `personalization.personalization_factors` | Required if `user_id` supplied |
| Personalization guidance | `{risk_sensitivity, position_sensitivity, accumulation_bias}` | Member 3 `personalization.personalization_guidance` | Required if `user_id` supplied |
| RAG evidence chunks | `[{text, similarity_score, source:{...9 fields...}}]` | Member 2 `/retrieve.results[]` | Optional (may be empty array; `status: NO_RESULTS`) |
| Source attribution | `{document_id, title, company, symbol, document_type, section, source_name, source_type, published_date}` | Member 2 `/retrieve.results[].source` | Required on every result that exists (guaranteed by Member 2's own contract — no partial attribution) |
| Reasoning trace | `[{step, stage, summary, detail, timestamp}]`, fixed 8 entries | Member 4 `AnalysisResult.reasoning_trace` | Required, fixed length 8, fixed order |
| Metrics: per-agent latency | `int ms` | Member 4 `agent_outputs[].latency_ms` | Required per agent |
| Metrics: total analysis latency | `int ms` | Member 4 `AnalysisResult.total_latency_ms` (agent-only) + gateway-measured upstream fetch time | Required (see §8 for real-vs-simulated split) |
| Metrics: failed agents | `string[]` | Member 4 `AnalysisResult.failed_agents` | Required (may be empty) |
| Data quality: market | `enum OK\|DEGRADED\|UNAVAILABLE` | Member 1 `data_status` | Required |
| Data quality: RAG | `enum OK\|NO_RESULTS\|DEGRADED` | Member 2 `status` | Required |
| Data quality: agents/overall | `enum HIGH\|MEDIUM\|LOW\|NONE` | Member 4 `AnalysisResult.data_quality` | Required |
| Loading state | n/a (frontend-only) | Member 5 gateway (single request in flight) | Required UI state |
| Error state | `{code, message}` normalized | Member 5 gateway (`normalize_error`, see audit §8.2) | Required UI state |
| Degraded state | derived from the `data_quality` object above | Member 5 gateway | Required UI state |

---

# 2. Actual Module Interfaces

Taken verbatim from the audited code — no invented fields.

### Member 1 — Market + Signal Engine
```
GET /signals/{symbol}?lookback=N   (lookback optional, 1–60, default 5)

→ 200 OK
{
  "symbol": "str", "timestamp": "ISO-8601",
  "market_data": {"price":0.0,"open":0.0,"high":0.0,"low":0.0,"close":0.0,"volume":0.0,"currency":"INR"} | null,
  "signals": {
    "price_momentum": {"name":"str","signal":"BULLISH|NEUTRAL|BEARISH|UNAVAILABLE","value":0.0|null,"confidence":0.0,"evidence":["str"]},
    "volume_anomaly": { "...same shape..." },
    "rsi": { "...same shape..." }
  },
  "overall_signal": "BULLISH|NEUTRAL|BEARISH",
  "confidence": 0.0,
  "reasoning": ["str"],
  "data_status": "OK|DEGRADED|UNAVAILABLE",
  "warnings": ["str"]
}

→ 404 { "error": {"code":"SYMBOL_NOT_FOUND","message":"str"} }
→ 422 { "error": {"code":"INVALID_REQUEST","message":"str"} }
```

### Member 2 — RAG
```
POST /retrieve
{ "query":"str (required)", "symbol":"str|null", "document_type":"str|null", "top_k":5 }

→ 200 OK
{
  "query":"str","symbol":"str|null",
  "results":[{"chunk_id":"str","text":"str","similarity_score":0.0,
              "source":{"document_id":"str","title":"str","company":"str","symbol":"str",
                        "document_type":"str","section":"str","source_name":"str",
                        "source_type":"str","published_date":"YYYY-MM-DD"}}],
  "status":"OK|NO_RESULTS|DEGRADED",
  "warnings":["str"]
}

→ 400 { "error": {"code":"INVALID_QUERY"|"INVALID_REQUEST","message":"str"} }
→ 503 { "error": {"code":"VECTOR_STORE_UNAVAILABLE","message":"str"} }
```

### Member 3 — Profile + Portfolio
```
GET /users/{user_id}/personalization/{symbol}

→ 200 OK
{
  "user_id":"str","symbol":"str",
  "profile": {"risk_tolerance":"conservative|moderate|aggressive","investment_horizon_years":0},
  "portfolio_context": {"portfolio_value":0.0,"current_position_percentage":0.0,"number_of_holdings":0,"concentration_level":"none|low|moderate|elevated|high"},
  "watchlist": {"is_watchlisted": true},
  "personalization_factors": ["str"],
  "personalization_guidance": {"risk_sensitivity":"high|medium|low","position_sensitivity":"high|medium|low","accumulation_bias":"cautious|willing|balanced|neutral"}
}

→ 404 { "detail": "str" }   ← NOTE: different error shape than Members 1/2 (no "code" field)
```
Supplementary calls used to build `portfolio`:
```
GET /users/{user_id}/portfolio       → {"user_id","total_value","holdings":[{"symbol","quantity","average_price","current_price","value","position_percentage"}]}
GET /users/{user_id}/portfolio/risk  → {"user_id","portfolio_value","number_of_holdings","largest_position":{"symbol","percentage"}|null,"top_3_concentration","concentration_level","risk_flags":["str"]}
```

### Member 4 — Agents + Orchestrator + Synthesis
**Not HTTP.** In-process Python call only:
```python
result = await analyze(
    symbol: str,
    market_data: dict|None,   # gateway-adapted Member 1 output
    rag_context: dict|None,   # gateway-adapted Member 2 output
    user_profile: dict|None,  # gateway-adapted Member 3 output
) -> AnalysisResult

payload = result.to_frontend_dict()
```
```json
{
  "symbol":"str","final_signal":"BULLISH|MODERATELY_BULLISH|NEUTRAL|MODERATELY_BEARISH|BEARISH",
  "confidence":0.0,"recommendation":"BUY|ACCUMULATE|HOLD|REDUCE|SELL","reasoning":["str"],
  "agent_outputs":[{"agent":"technical|fundamental|sentiment","status":"success|insufficient_data|failed",
                     "signal":"BULLISH|NEUTRAL|BEARISH","confidence":0.0,"reasoning":["str"],
                     "evidence":[{"source":"str","section":"str","text":"str","score":0.0}],
                     "data_quality":"HIGH|MEDIUM|LOW|NONE","latency_ms":0,"errors":[]}],
  "sources":[{"...same Evidence shape..."}],
  "risk_factors":["str"],"personalization":["str"],
  "data_quality":"HIGH|MEDIUM|LOW|NONE","failed_agents":["str"],
  "reasoning_trace":[{"step":1,"stage":"input_received","summary":"str","detail":{},"timestamp":"ISO-8601"}],
  "directional_score":0.0,"risk_level":"LOW|MODERATE|HIGH|CRITICAL",
  "user_id":"str","total_latency_ms":0,"generated_at":"ISO-8601"
}
```
Never raises for data problems — degrades via `failed_agents`/`data_quality` instead of throwing.

---

# 3. Normalized Member 5 Contract

The response the frontend actually consumes, `GET/POST` from Member 5's gateway. Field-by-field, with transformation notes.

```json
{
  "symbol": "string — required — passthrough from request",
  "market": {
    "price": "float|null — required — Member 1 market_data.price",
    "ohlc": "{open,high,low,close}|null — required key — Member 1 market_data.{open,high,low,close}",
    "volume": "float|null — optional — Member 1 market_data.volume",
    "currency": "string — optional (default INR) — Member 1 market_data.currency",
    "as_of": "ISO-8601 — required — Member 1 timestamp, renamed",
    "data_status": "OK|DEGRADED|UNAVAILABLE — required — Member 1 data_status, passthrough",
    "warnings": "string[] — optional — Member 1 warnings, passthrough"
  },
  "signals": {
    "price_momentum": "{signal,value,confidence,evidence[]} — required key — Member 1 signals.price_momentum, passthrough",
    "volume_anomaly": "same — required key — Member 1 signals.volume_anomaly, passthrough",
    "rsi": "same — required key — Member 1 signals.rsi, passthrough",
    "overall_signal": "BULLISH|NEUTRAL|BEARISH — required — Member 1 overall_signal, passthrough",
    "overall_confidence": "float — required — Member 1 confidence, renamed to avoid clashing with synthesis.confidence"
  },
  "agents": {
    "technical": "{status,signal,confidence,reasoning[],evidence[],data_quality,latency_ms,errors[]} — required key — Member 4 agent_outputs[agent=technical], passthrough",
    "fundamental": "same shape — required key — Member 4 agent_outputs[agent=fundamental], passthrough",
    "sentiment": "same shape — required key — Member 4 agent_outputs[agent=sentiment], passthrough (expect low confidence — no real sentiment source, see §12)"
  },
  "synthesis": {
    "final_signal": "enum (5 states) — required — Member 4 AnalysisResult.final_signal",
    "confidence": "float — required — Member 4 AnalysisResult.confidence",
    "recommendation": "enum (5 states) — required — Member 4 AnalysisResult.recommendation",
    "directional_score": "float — required — Member 4 AnalysisResult.directional_score",
    "risk_level": "LOW|MODERATE|HIGH|CRITICAL — required — Member 4 AnalysisResult.risk_level",
    "risk_factors": "string[] — required (may be empty) — Member 4 AnalysisResult.risk_factors",
    "personalization": "string[] — required (may be empty) — Member 4 AnalysisResult.personalization",
    "reasoning": "string[] — required — Member 4 AnalysisResult.reasoning"
  },
  "profile": {
    "user_id": "string|null — optional (only if user_id passed in request) — Member 3 personalization.user_id",
    "risk_tolerance": "conservative|moderate|aggressive|null — optional — Member 3 personalization.profile.risk_tolerance",
    "investment_horizon_years": "int|null — optional — Member 3 personalization.profile.investment_horizon_years",
    "personalization_factors": "string[] — optional — Member 3 personalization.personalization_factors",
    "personalization_guidance": "{risk_sensitivity,position_sensitivity,accumulation_bias}|null — optional — Member 3 personalization.personalization_guidance",
    "is_watchlisted": "bool|null — optional — Member 3 personalization.watchlist.is_watchlisted"
  },
  "portfolio": {
    "total_value": "float — optional (0 default) — Member 3 /portfolio.total_value",
    "holdings": "[{symbol,quantity,average_price,current_price,value,position_percentage}] — optional (empty default) — Member 3 /portfolio.holdings, passthrough",
    "concentration_level": "none|low|moderate|elevated|high|null — optional — Member 3 /portfolio/risk.concentration_level",
    "top_3_concentration": "float|null — optional — Member 3 /portfolio/risk.top_3_concentration",
    "largest_position": "{symbol,percentage}|null — optional — Member 3 /portfolio/risk.largest_position",
    "risk_flags": "string[] — optional (empty default) — Member 3 /portfolio/risk.risk_flags"
  },
  "evidence": "[{chunk_id,text,similarity_score,source:{9 fields}}] — optional (empty array valid) — Member 2 /retrieve.results[], passthrough unmodified (full attribution preserved — see §10)",
  "reasoning_trace": "[{step,stage,summary,detail,timestamp}] — required, fixed length 8, fixed order — Member 4 AnalysisResult.reasoning_trace, passthrough",
  "metrics": {
    "total_latency_ms": "int — required — REAL: gateway-measured wall-clock for the whole /api/analyze call",
    "per_module_latency_ms": "{market,rag,profile,agents} — required — REAL: gateway-measured per upstream call",
    "agent_latency_ms": "{technical,fundamental,sentiment} — required — REAL: Member 4 agent_outputs[].latency_ms, passthrough",
    "agents_completed": "int — required — DERIVED: count of agent_outputs where status==success",
    "agents_failed": "string[] — required (may be empty) — REAL: Member 4 AnalysisResult.failed_agents, passthrough",
    "confidence": "float — required — REAL: Member 4 AnalysisResult.confidence, passthrough (duplicate of synthesis.confidence for convenience)",
    "portfolio_concentration": "string|null — optional — REAL: Member 3 concentration_level, passthrough (duplicate of portfolio.concentration_level for convenience)",
    "signal_accuracy": "OMITTED — no historical/backtested accuracy data exists anywhere in Members 1–4; do not fabricate this field (see §8)"
  },
  "data_quality": {
    "overall": "HIGH|MEDIUM|LOW|NONE — required — Member 4 AnalysisResult.data_quality, passthrough",
    "market": "OK|DEGRADED|UNAVAILABLE — required — Member 1 data_status, passthrough",
    "rag": "OK|NO_RESULTS|DEGRADED — required — Member 2 status, passthrough",
    "profile": "OK|MISSING — required — DERIVED: OK if user_id was supplied and Member 3 responded 200, else MISSING"
  }
}
```

Note on `agents.risk`: dropped as its own object (per audit §9) because Member 4 does not emit a standalone risk-agent payload — `synthesis.risk_level` and `synthesis.risk_factors` are the actual risk output. Do not invent a fourth `agents.risk` block with fields that don't exist in the code.

---

# 4. Frontend API

**Primary endpoint:**
```
POST /api/analyze
```

**Request body:**
```json
{
  "symbol": "string, required, e.g. \"RELIANCE\"",
  "user_id": "string, optional — omit for an anonymous/no-personalization view",
  "lookback": "int, optional, 1–60, default 5 — forwarded to Member 1"
}
```

**Response body:** the §3 normalized contract, `200 OK`.

**Errors** (normalized shape returned by the gateway regardless of which upstream failed):
```json
{ "error": { "code": "string", "message": "string", "source": "market|rag|profile|agents|gateway" } }
```
| HTTP status | `code` | Trigger |
|---|---|---|
| 404 | `SYMBOL_NOT_FOUND` | Member 1 returned 404 for the symbol |
| 404 | `USER_NOT_FOUND` | Member 3 returned 404 for the user_id (translated from its `{"detail":...}` shape) |
| 422 | `INVALID_REQUEST` | Bad `lookback`, empty `symbol`, or Member 1/2 422/400 |
| 503 | `VECTOR_STORE_UNAVAILABLE` | Member 2 Chroma unavailable |
| 502 | `UPSTREAM_UNAVAILABLE` | Any of Members 1/2/3 unreachable (connection refused/timeout) |
| 500 | `INTERNAL_ERROR` | Gateway-side failure, or `analyze()` raised unexpectedly (should not happen per Member 4's contract, but the gateway still needs a catch-all) |

**Loading behavior:** Single request in flight per analysis. The frontend shows one loading state for the whole `/api/analyze` call (the gateway internally parallelizes Members 1–3 via `asyncio.gather`, then calls Member 4 — this is invisible to the frontend as separate loading phases unless streaming is added later, which is out of scope here).

**Degraded behavior:** A `200 OK` response can still carry degraded data — the frontend must inspect `data_quality` and each `agents.*.status` / `agents.*.data_quality` field on every successful response, not just on error responses. A `200` is not a signal that everything is high quality.

---

# 5. Adapter Requirements

| Module | Adapter required? | Direction |
|---|---|---|
| Member 1 | **Yes** | `Frontend → Gateway → market_adapter.py → Member 1 HTTP` — maps Member 1's `SignalResponse` fields into §3's `market`/`signals` blocks (mostly passthrough/rename; see audit §8.4 for the deeper mapping into Member 4's `market_data`/`indicators` input, which is a *second*, internal adapter the gateway also needs before calling `analyze()`) |
| Member 2 | **Yes** | `Frontend → Gateway → rag_adapter.py → Member 2 HTTP` — maps `results[]`/`similarity_score`/`source` (object) into Member 4's expected `chunks[]`/`score`/`source` (string) shape for the `analyze()` call, while the **unmodified** Member 2 `results[]` (with full 9-field `source` objects) is what actually flows into the frontend's `evidence` field per §3 and §10 |
| Member 3 | **Yes** | `Frontend → Gateway → profile_adapter.py → Member 3 HTTP` — maps `personalization`/`portfolio`/`portfolio/risk` responses into Member 4's expected `user_profile` dict (renames, buckets `investment_horizon_years` into a horizon bucket, defaults fields with no source data — `max_position_pct`, `cash_pct`, `behavioral_flags` — per audit §8.6); the **unmodified** Member 3 responses are what populate the frontend's `profile`/`portfolio` blocks |
| Member 4 | **No HTTP adapter — an in-process call wrapper instead** | `Frontend → Gateway → (direct await analyze(...))` — no network adapter needed since Member 4 is already a Python function; the "adapter" work here is entirely on the *input* side (feeding it Member 1/2/3's adapted data) and is covered by the three adapters above |

No teammate module (`member1/`–`member4/` source) is modified by any of this — every adapter listed above lives only inside Member 5's gateway codebase, consistent with the audit's finding that this is achievable without touching upstream code.

---

# 6. UI Mapping

| UI Component | Data Source | Contract Field |
|---|---|---|
| Stock Header | Member 1 | `symbol`, `market.price`, `market.data_status` |
| Price Chart | Member 1 | `market.ohlc`, `market.volume`, `market.as_of` |
| Market Signal | Member 1 | `signals.overall_signal`, `signals.overall_confidence` |
| Signal Dimensions | Member 1 | `signals.price_momentum`, `signals.volume_anomaly`, `signals.rsi` |
| Technical Agent | Member 4 | `agents.technical` |
| Fundamental Agent | Member 4 | `agents.fundamental` |
| Sentiment Agent | Member 4 | `agents.sentiment` |
| Risk Agent | Member 4 (no dedicated agent object — see §3 note) | `synthesis.risk_level`, `synthesis.risk_factors` |
| Synthesis | Member 4 | `synthesis.final_signal`, `synthesis.confidence`, `synthesis.recommendation`, `synthesis.directional_score` |
| WHY THIS RESULT | Member 4 | `synthesis.reasoning`, `reasoning_trace[6]` (`risk_adjustment` stage — has the exposure/concentration/downgrade detail per Member 4's own README guidance) |
| RAG Evidence | Member 2 (unmodified) | `evidence[]` (each with full `source` object) |
| Investor Profile | Member 3 | `profile.risk_tolerance`, `profile.investment_horizon_years`, `profile.personalization_factors`, `profile.personalization_guidance` |
| Portfolio | Member 3 | `portfolio.total_value`, `portfolio.holdings` |
| Risk/Concentration | Member 3 | `portfolio.concentration_level`, `portfolio.top_3_concentration`, `portfolio.largest_position`, `portfolio.risk_flags` |
| Reasoning Trace | Member 4 | `reasoning_trace[]` (render in `step` order using `stage` + `summary`; use `detail` for an expandable view) |
| Metrics | Gateway + Member 4 | `metrics.*` (see §8 for real vs. derived) |
| Data Quality | Member 1 + Member 2 + Member 4 + Gateway | `data_quality.*` |

---

# 7. Error and Degraded States

| Scenario | Frontend behavior |
|---|---|
| **Market service (Member 1) fails/unreachable** | Show `market`/`signals` sections as "Market data unavailable" (use `502 UPSTREAM_UNAVAILABLE`). Do not block Technical/Fundamental/Sentiment/Synthesis rendering — `analyze()` degrades gracefully with missing `market_data`, so the rest of the dashboard can still render with lower `data_quality`. |
| **RAG (Member 2) fails/unreachable** | Show `evidence` section as "No supporting documents available" rather than an error blob. This is functionally identical to a normal empty-retrieval response (`status: NO_RESULTS`) from the frontend's point of view — treat connection failure and legitimate zero-results the same way in the UI, distinguished only by an optional tooltip/log detail. |
| **Profile service (Member 3) fails/unreachable, or no `user_id` supplied** | `profile`/`portfolio` sections show "Personalization unavailable — showing generic analysis." All other sections (market, signals, agents, synthesis) render normally; `analyze()` accepts `user_profile=None` and applies neutral defaults per its own contract. |
| **Individual agent fails** (`agent_outputs[].status == "failed"`) | That one agent card shows a "This agent could not complete" state with its `errors[]` message if present. **The other agents, synthesis, and the rest of the dashboard render normally** — this is the explicit design intent stated in the prompt and matches Member 4's own contract (`failed_agents` populated, everything else still returned). |
| **Synthesis fails** | Per Member 4's contract this cannot happen from bad data alone (`analyze()` never raises for data problems) — treat only as a `500 INTERNAL_ERROR` from the gateway. Show a full-page "Analysis failed, please retry" state, since without `synthesis` there is no coherent recommendation to anchor the rest of the dashboard around. |
| **Unknown stock symbol** | `404 SYMBOL_NOT_FOUND` from Member 1 → show "Unknown symbol" at the search/header level before attempting to render any dashboard section. |
| **Missing document (RAG has nothing for this symbol)** | Same as "RAG fails" above — `status: NO_RESULTS` is a valid 200 response, not an error; show empty-state copy, not an error banner. |
| **Incomplete market data** (`data_status: DEGRADED`, some `signals.*.signal == UNAVAILABLE`) | Render all three signal dimension cards; any with `signal: UNAVAILABLE` show "Insufficient data for this dimension" instead of a value, using the `evidence[]` text Member 1 already provides explaining why. Show a small "Degraded" badge near the market header rather than hiding the section. |

**Governing rule for this whole section (explicit in the source prompt):** one failed agent, one missing document set, or one degraded upstream module must never blank out the entire dashboard. Each section degrades independently based on its own `status`/`data_quality` field.

---

# 8. Metrics Contract

| Field | Real or Simulated | Definition |
|---|---|---|
| `metrics.agent_latency_ms.{technical,fundamental,sentiment}` | **Real** | Directly from Member 4 `agent_outputs[].latency_ms` — measured inside Member 4's own `BaseAgent.run` timing, not estimated |
| `metrics.total_latency_ms` | **Real** | Gateway wall-clock for the entire `/api/analyze` request (upstream fetches + adapter time + `analyze()` call) |
| `metrics.per_module_latency_ms.{market,rag,profile}` | **Real** | Gateway-measured time for each individual `httpx` call to Members 1/2/3 |
| `metrics.per_module_latency_ms.agents` | **Real** | Member 4's own `AnalysisResult.total_latency_ms` (the agents/synthesis portion only), passthrough |
| `metrics.agents_completed` | **Derived (real, computed)** | Count of `agent_outputs[]` where `status == "success"` — computed from real data, not simulated |
| `metrics.agents_failed` | **Real** | Passthrough of Member 4 `AnalysisResult.failed_agents` |
| `metrics.confidence` | **Real** | Passthrough of Member 4 `AnalysisResult.confidence` |
| `metrics.portfolio_concentration` | **Real** | Passthrough of Member 3 `concentration_level` |
| `metrics.data_quality (overall/market/rag)` | **Real** | Passthrough of each module's own self-reported quality/status enum |
| `signal_accuracy` / any backtested or "simulated accuracy" figure | **Not available — do not display.** | No module in this project computes historical accuracy, backtested returns, or win-rate against forward prices. Member 1's README is explicit that its mock provider is a random walk and "signal accuracy against forward returns cannot be evaluated from it." **Any accuracy metric shown in the UI would be fabricated.** If a "confidence" gauge is wanted for visual appeal, label it exactly as `confidence` (already real, from `synthesis.confidence`) — never relabel it as "accuracy." |

**Explicit distinction for the UI:** every metric in this contract is a real, measured or passthrough value. There is no simulated/mocked metric in the normalized contract — where real data doesn't exist (accuracy), the field is omitted rather than faked, per the audit's data-quality-honesty principle.

---

# 9. Reasoning Trace Contract

Member 4's `reasoning_trace` is **always exactly 8 entries, in this fixed order**, each shaped `{step, stage, summary, detail, timestamp}`:

| step | stage | Frontend rendering |
|---|---|---|
| 1 | `input_received` | "Inputs received" — summary text as-is |
| 2 | `agents_started` | "Analysis started" — summary text as-is |
| 3 | `technical_result` | Links to the Technical Agent card |
| 4 | `fundamental_result` | Links to the Fundamental Agent card |
| 5 | `sentiment_result` | Links to the Sentiment Agent card |
| 6 | `conflict_resolution` | "How disagreements were resolved" — key panel for cross-agent conflicts |
| 7 | `risk_adjustment` | The primary source for the "WHY THIS RESULT" panel — contains exposure/concentration/downgrade detail per Member 4's own docs |
| 8 | `final_synthesis` | "Final result" — links to the Synthesis centerpiece |

The requested pipeline label set (`Market Data → Signal Engine → Technical Agent → RAG Retrieval → Fundamental Agent → Sentiment Agent → Risk Agent → Synthesis → Personalization → Final Result`) does **not** map one-to-one onto Member 4's 8 fixed stages — Member 4 has no separate `rag_retrieval`, `risk_agent`, or `personalization` trace steps; those concepts are folded into `technical_result`/`fundamental_result`/`sentiment_result` (evidence/citations already embedded) and `risk_adjustment`/`final_synthesis` respectively. **The frontend should visualize the actual 8-stage trace above**, optionally with a decorative "pipeline" header graphic that groups stages 1–2 as "Data Gathering," 3–5 as "Agent Analysis," 6–7 as "Risk & Conflict Resolution," and 8 as "Final Result" — but the underlying data-bound trace must use the real 8 entries, not an invented 10-step list.

Per Member 4's own integration guidance: **the frontend only strictly needs `step`, `stage`, and `summary`** for the primary view; `detail` is available for an expandable/"show more" interaction per step.

---

# 10. RAG Attribution Contract

Full attribution path: `RAG → Fundamental Agent → Synthesis → API Gateway → Frontend`.

**Exact source fields available (from Member 2's `SourceAttribution` model, always fully populated on every result):**
```
document_id     str
title           str
company         str
symbol          str
document_type   str  ("annual_report" | "earnings_report" | "earnings_transcript" | "company_disclosure")
section         str
source_name     str
source_type     str  (e.g. "synthetic")
published_date  date (YYYY-MM-DD)
```

**How it survives the pipeline:**
1. Member 2 → returns full `SourceAttribution` (9 fields) per result.
2. → Fundamental Agent (Member 4): consumes a *simplified* `evidence` shape internally (`{source, section, text, score}` where `source` is a plain string) via the RAG adapter (audit §8.5) — this is a **narrower** shape than Member 2's original, used only for Member 4's own reasoning/citation text.
3. → Synthesis (Member 4): `AnalysisResult.sources` carries the same simplified `Evidence` shape forward (`source, section, text, score` — string source, not the full 9-field object).
4. → API Gateway: **the gateway should not rely solely on Member 4's simplified `sources` for the frontend's citation display.** Instead, populate the frontend's `evidence[]` field (§3) directly from Member 2's **unmodified** `/retrieve` response, which still has the full 9-field `source` object. This preserves complete attribution (company, document type, publication date, source type) that would otherwise be lost in Member 4's narrower internal shape.
5. → Frontend: renders `evidence[].source.{title, company, document_type, section, source_name, source_type, published_date}` as a full citation block per Member 2's own recommended minimum (`Source: <title> / Section: <section> / Source type: <source_type>`), plus `evidence[].similarity_score` as a relevance indicator.

**Contract requirement:** the gateway must keep a direct reference to Member 2's raw `/retrieve.results[]` alongside whatever it feeds into `analyze()`, specifically so step 4 above doesn't lose attribution fidelity by relying only on Member 4's pass-through `sources`.

---

# 11. Stitch Design Specification

**Product:** A professional multi-agent financial intelligence terminal for retail investors — dark-first, data-dense, and explicitly built around *explainability* (every number on screen must be traceable to a reasoning step or a cited source).

**Visual language**
- Dark-first theme: near-black base (`#0A0E14`-class), high-contrast text, restrained accent palette — one accent for bullish (green-leaning), one for bearish (red-leaning), one neutral accent for informational/UI chrome. Avoid saturated "hackathon gradient" styling — favor flat panels, thin 1px borders, and monospace/tabular figures for numeric data (prices, percentages, confidence scores) to read as a trading-terminal, not a marketing page.
- Typography: a clean grotesque/sans for labels and body, a monospace face for all numeric values (price, %, confidence, latency) to reinforce the "terminal" feel and keep columns of numbers aligned.
- Density over whitespace: this is an analyst tool. Prefer compact cards with clear section dividers over large decorative empty space.

**Primary layout (top to bottom / left to right)**
1. **Stock/Watchlist selection bar** — symbol search + a short watchlist strip (Member 3's `is_watchlisted` flag drives a star/toggle state).
2. **Market Overview header** — symbol, price, OHLC micro-stats, `data_status` badge (OK/Degraded/Unavailable in distinct colors), overall signal chip.
3. **Signal Dimensions row** — three compact cards (Momentum, Volume, RSI), each showing signal label, confidence as a small radial/bar, and a one-line evidence excerpt.
4. **Agent visualization panel** — three (not four — no standalone risk agent exists) agent cards side by side: Technical, Fundamental, Sentiment. Each card: status pill (success/insufficient_data/failed), signal, confidence bar, top reasoning line, data_quality badge. A failed/insufficient-data card visually recedes (dimmed, not hidden) rather than breaking the row.
5. **Synthesis centerpiece** — the visual anchor of the page: large `final_signal` + `recommendation` display (5-state color/iconography), confidence gauge, directional score, risk_level badge. This should be the single largest, most prominent element on the screen.
6. **"WHY THIS RESULT" interaction** — an expandable panel/drawer triggered from the synthesis centerpiece, populated from `synthesis.reasoning` + the `risk_adjustment` trace step's `detail`. Should feel like clicking "explain this number," not a separate page.
7. **Reasoning trace strip** — a horizontal 8-node stepper (per §9) below or beside the synthesis centerpiece; each node expandable to show `detail`.
8. **RAG Evidence / Citations panel** — a scrollable list of cited chunks, each showing the excerpt text, similarity score, and the full attribution block (title, company, document type, section, source type, published date) per §10 — styled like a research citation list, not a chat bubble.
9. **Investor Profile & Portfolio sidebar** — risk tolerance, horizon, personalization factors/guidance, portfolio total value, holdings table, concentration level with a visual concentration meter, risk flags as small tags. This is the "why is my advice different from someone else's" section — keep it visually connected to the synthesis centerpiece (e.g. a connecting line or shared color accent) since Member 4's headline demo depends on this link being legible.
10. **Metrics strip (footer or collapsible panel)** — per-agent latency, total latency, agents completed/failed, data quality badges. Small, technical, secondary in visual weight — this is for judges/debugging, not the primary investor-facing narrative.

**States to design explicitly:** loading (skeleton, not spinner, for the dense card layout), partial-degraded (badges + dimmed sections per §7), and full-error (symbol not found / analysis failed) as distinct, deliberate screens — not generic error toasts, given how central the "one failure shouldn't kill the dashboard" requirement is to this project.

---

# 12. Integration Risks

(Restated/prioritized from the audit for frontend-contract purposes — full detail in `MEMBER5_INTEGRATION_AUDIT.md` §10.)

1. Ports 8000 collide across Members 1/2/3 — gateway must target explicit distinct ports.
2. Member 4 has no HTTP surface — the frontend must never be told to "call the orchestrator"; only the gateway touches it, in-process.
3. Sentiment has no real data source anywhere in the project — the Sentiment Agent card will realistically show `insufficient_data`/low confidence for the whole demo unless a synthetic feed is built; design the UI so this doesn't look like a bug (§11 point 4's "dimmed, not hidden" treatment matters most here).
4. Member 3's error shape (`{"detail":...}`) differs from Members 1/2 (`{"error":{"code","message"}}`) — must be normalized in the gateway before it ever reaches the frontend's error-handling code, or the "unknown user" state will silently break.
5. Full RAG attribution is only preserved end-to-end if the gateway keeps Member 2's raw response for the frontend, rather than relying on Member 4's narrower internal `sources` shape (§10) — a frontend built only against Member 4's `AnalysisResult.sources` will show incomplete citations.
6. No signal-accuracy/backtest data exists anywhere — any "accuracy" UI element must be cut or explicitly relabeled as `confidence` (§8).
7. Member 4's headline "same signal, different advice" demo depends on profile fields (`max_position_pct`, `cash_pct`, `behavioral_flags`) that Member 3 doesn't collect — decide before UI work whether the demo relies on Member 3's real users or Member 4's internal mocks for that specific narrative beat.

---

# 13. Recommended Build Order

1. **Gateway skeleton first** — stand up `/api/analyze` returning a hardcoded §3-shaped stub, so frontend work can start against a stable contract immediately without waiting for adapters.
2. **Adapters (market → rag → profile)**, in that order — market is the simplest mapping, profile is the most involved (field derivation + defaults).
3. **Wire the real `analyze()` call** once all three adapters produce valid Member 4 input shapes; validate against Member 4's own `mocks/*.json` first before touching live Members 1–3.
4. **Assemble the true §3 normalized response** (real upstream data replacing the stub), including the "keep Member 2's raw attribution" requirement from §10.
5. **Error normalization layer** (§4/§7) — build this before frontend error-state work depends on it.
6. **Frontend, section by section, against the now-stable real contract**: Stock Header/Price Chart → Signal Dimensions → Agent panel → Synthesis centerpiece → WHY THIS RESULT → Reasoning trace → RAG Evidence → Profile/Portfolio sidebar → Metrics strip — in roughly this order, since each later section depends on data shapes proven out by the earlier ones.
7. **Degraded/error state pass** — deliberately kill each upstream module one at a time and confirm the dashboard degrades per §7 without going blank.
8. **Final end-to-end pass** — all five processes running on their assigned ports (§11 of the audit), full symbol + user_id combinations exercised, before visual polish.
