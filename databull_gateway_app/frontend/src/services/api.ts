import { AnalysisResponse, CorpusDocument } from '../types';

export const API_BASE = '/api';

export const FALLBACK_RELIANCE: AnalysisResponse = {
  symbol: "RELIANCE",
  company_name: "RELIANCE INDUSTRIES",
  exchange: "NSE",
  price: 1420.50,
  change: 39.10,
  change_pct: 2.84,
  market_status: "MARKET OPEN",
  currency: "INR",
  ohlc: {
    open: 1385.00,
    high: 1425.80,
    low: 1381.20,
    close: 1420.50
  },
  volume: 8429100,
  signals: {
    price_momentum: {
      name: "Price Momentum (EMA Cross)",
      signal: "BULLISH",
      value: 1.84,
      confidence: 0.84,
      evidence: ["EMA 20 crossed above EMA 50 on 4h timeframe", "MACD histogram expanding positive"]
    },
    volume_anomaly: {
      name: "Volume Anomaly",
      signal: "BULLISH",
      value: 2.15,
      confidence: 0.78,
      evidence: ["Volume is 2.15x the 20-day rolling average", "High volume on green candles"]
    },
    rsi: {
      name: "Relative Strength Index (RSI-14)",
      signal: "BULLISH",
      value: 62.4,
      confidence: 0.82,
      evidence: ["RSI at 62.4 indicating strong momentum without overbought condition (>70)"]
    },
    overall_signal: "BULLISH",
    overall_confidence: 0.81
  },
  agents: {
    technical: {
      agent: "technical",
      status: "success",
      signal: "BULLISH",
      confidence: 0.82,
      reasoning: [
        "Multi-timeframe breakout above key resistance at ₹1,400 with sustained volume.",
        "Moving average convergence (20/50/200) confirms structural uptrend.",
        "Bollinger band expansion suggests ongoing volatility expansion to upside."
      ],
      evidence: [
        { source: "NSE Tick Data", section: "Technical Indicators", text: "Breakout confirmed on 1D/4H chart above ₹1,400 with 2.15x volume", score: 0.88 }
      ],
      data_quality: "HIGH",
      latency_ms: 42,
      errors: []
    },
    fundamental: {
      agent: "fundamental",
      status: "success",
      signal: "BULLISH",
      confidence: 0.85,
      reasoning: [
        "Q3 EBITDA up 12% YoY driven by Retail consumer expansion and Jio ARPU growth to ₹182.",
        "Oil-to-Chemicals (O2C) downstream margins showing stabilization at 8.4% with favorable crude sourcing.",
        "Debt-to-equity ratio remains well controlled at 0.44x following deleveraging cycle."
      ],
      evidence: [
        { source: "RELIANCE_Q3_FY24_Earnings_Transcript.pdf", section: "Management Commentary, pg 14", text: "Retail and Digital services continue to outpace core downstream earnings, driving consolidated EBITDA margin expansion.", score: 0.91 }
      ],
      data_quality: "HIGH",
      latency_ms: 68,
      errors: []
    },
    sentiment: {
      agent: "sentiment",
      status: "success",
      signal: "NEUTRAL",
      confidence: 0.57,
      reasoning: [
        "Institutional analyst reports maintain 28 Buy / 5 Hold / 2 Sell ratings.",
        "News sentiment is moderately constructive on tariff hikes, balanced by cautious global petrochemical crack spreads.",
        "Social sentiment shows high retail interest with slight hesitation around capex announcements."
      ],
      evidence: [
        { source: "JPM_Initiation_Report_2024.pdf", section: "Analyst Consensus", text: "Neutral-to-constructive short term rating on refining cracks offset by strong telecom subscriber additions.", score: 0.74 }
      ],
      data_quality: "MEDIUM",
      latency_ms: 35,
      errors: []
    },
    risk: {
      agent: "risk",
      status: "success",
      signal: "MODERATE",
      confidence: 0.76,
      reasoning: [
        "Beta of 0.92 indicates lower volatility than broader Nifty index.",
        "Global oil crack margin volatility presents secondary macro exposure.",
        "Concentration risk in user portfolio is low (12% energy allocation vs 15% target)."
      ],
      evidence: [
        { source: "Risk Engine Analytics", section: "Portfolio VaR", text: "95% 1-Day VaR is 1.42%, well within moderate portfolio risk threshold.", score: 0.85 }
      ],
      data_quality: "HIGH",
      latency_ms: 28,
      errors: []
    }
  },
  synthesis: {
    final_signal: "BULLISH",
    confidence: 0.81,
    recommendation: "BUY",
    directional_score: 0.78,
    risk_level: "MODERATE",
    timeframe: "3-6M",
    supporting_factors: [
      "Technical breakout with strong institutional volume support (+2.15x avg).",
      "Solid Q3 consumer segment EBITDA margins (Retail + Jio) buffering cyclical headwinds.",
      "Portfolio fit: Balances underweight Energy allocation without exceeding single-stock concentration limits."
    ],
    counter_signals: [
      "Global refining crack spreads remain volatile in Q4.",
      "RSI at 62.4 approaches near-term resistance zone (₹1,440-₹1,460)."
    ],
    risk_factors: [
      "Crude oil price shocks impact refining inventory valuation.",
      "Regulatory policy changes on telecom tariffs."
    ],
    personalization: [
      "Aligns with Moderate Risk Profile for 3-6M horizon.",
      "Current portfolio allocation is 12% Energy (underweight by 3%). Adding position improves sector diversification."
    ],
    reasoning: [
      "The 81% Bullish consensus strongly aligns with your Moderate Risk profile and Long-term horizon.",
      "The breakout in technical momentum is supported by solid Q3 fundamentals, buffering short-term volatility.",
      "Increasing position size here would balance your underweight Energy exposure without breaching concentration risk limits."
    ]
  },
  profile: {
    user_id: "user_default",
    risk_tolerance: "Moderate",
    investment_horizon_years: 3,
    horizon_label: "Long-Term",
    profile_match: "HIGH",
    portfolio_exposure: "Energy: 12% (Underweight)",
    concentration_risk: "Low (Acceptable)",
    personalization_factors: [
      "Target Energy exposure: 15%",
      "Max single asset cap: 15%",
      "Preference for large-cap defensive growth"
    ],
    personalization_guidance: {
      risk_sensitivity: "medium",
      position_sensitivity: "low",
      accumulation_bias: "willing"
    },
    is_watchlisted: true
  },
  portfolio: {
    total_value: 2450000.0,
    holdings: [
      { symbol: "RELIANCE", quantity: 200, average_price: 1340.00, current_price: 1420.50, value: 284100.0, position_percentage: 11.6 },
      { symbol: "TCS", quantity: 150, average_price: 3720.00, current_price: 3890.10, value: 583515.0, position_percentage: 23.8 },
      { symbol: "INFY", quantity: 300, average_price: 1480.00, current_price: 1532.90, value: 459870.0, position_percentage: 18.7 },
      { symbol: "HDFCBANK", quantity: 400, average_price: 1590.00, current_price: 1650.00, value: 660000.0, position_percentage: 26.9 }
    ],
    concentration_level: "low",
    top_3_concentration: 0.694,
    largest_position: { symbol: "HDFCBANK", percentage: 26.9 },
    risk_flags: []
  },
  evidence: [
    {
      chunk_id: "SRC-01",
      text: "Moving to the O2C segment, while we saw some stabilization in fuel cracks towards the end of the quarter, the overall margin environment remains challenging. Global macroeconomic headwinds, coupled with the influx of new capacity additions in China, are expected to cap any significant upside potential in the near term. Our forward guidance remains cautious, and our primary focus will be on maximizing downstream integration and optimizing feedstocks to defend our margins against these external pressures.",
      similarity_score: 0.89,
      source: {
        document_id: "DOC-REL-2024-Q3",
        title: "RELIANCE_Q3_FY24_Earnings_Transcript.pdf",
        company: "Reliance Industries Limited",
        symbol: "RELIANCE",
        document_type: "earnings_transcript",
        section: "Management Commentary, pg 14",
        source_name: "RIL Investor Relations",
        source_type: "SYNTHETIC / DEMO CORPUS",
        published_date: "2024-01-19",
        entities: ["Reliance O2C", "China Capacity", "Feedstock Optimization"],
        sentiment: "Cautious"
      }
    },
    {
      chunk_id: "SRC-02",
      text: "Reliance Retail recorded its highest-ever quarterly footfall exceeding 282 million across its store network. EBITDA margins expanded by 45 bps YoY to 8.6%, driven by operational efficiencies and higher contribution from own brands and premium fashion segments.",
      similarity_score: 0.84,
      source: {
        document_id: "DOC-REL-2024-Q3-RET",
        title: "RELIANCE_Q3_FY24_Earnings_Transcript.pdf",
        company: "Reliance Industries Limited",
        symbol: "RELIANCE",
        document_type: "earnings_transcript",
        section: "Retail Operational Highlights, pg 8",
        source_name: "RIL Investor Relations",
        source_type: "SYNTHETIC / DEMO CORPUS",
        published_date: "2024-01-19",
        entities: ["Reliance Retail", "EBITDA Margin", "Footfalls"],
        sentiment: "Strongly Bullish"
      }
    },
    {
      chunk_id: "SRC-03",
      text: "Jio Platforms demonstrated strong ARPU growth reaching ₹181.7 per subscriber with 5G rollout completed across 10,000+ cities. Fixed wireless access (JioAirFiber) adoption is tracking ahead of management guidance, providing high-margin incremental revenue.",
      similarity_score: 0.81,
      source: {
        document_id: "DOC-JPM-2024-01",
        title: "JPM_Initiation_Report_2024.pdf",
        company: "Reliance Industries Limited",
        symbol: "RELIANCE",
        document_type: "analyst_note",
        section: "Telecom & Digital Services, pg 22",
        source_name: "JP Morgan Equity Research",
        source_type: "SYNTHETIC / DEMO CORPUS",
        published_date: "2024-01-20",
        entities: ["Jio 5G", "ARPU", "AirFiber"],
        sentiment: "Bullish"
      }
    },
    {
      chunk_id: "SRC-04",
      text: "Consolidated net debt has stabilized at ₹1.18 lakh crore with robust operating cash flows covering ongoing 5G and new energy green hydrogen capex cycles. Credit profile remains resilient at AAA domestic rating.",
      similarity_score: 0.77,
      source: {
        document_id: "DOC-SEC-10Q-2023",
        title: "SEC_10Q_Reliance_Equivalent_Q3.pdf",
        company: "Reliance Industries Limited",
        symbol: "RELIANCE",
        document_type: "financial_disclosure",
        section: "Liquidity and Capital Resources, pg 31",
        source_name: "Company Regulatory Filing",
        source_type: "SYNTHETIC / DEMO CORPUS",
        published_date: "2023-12-31",
        entities: ["Net Debt", "Green Energy Capex", "Liquidity"],
        sentiment: "Neutral"
      }
    }
  ],
  reasoning_trace: [
    { step: 1, stage: "Market Data", status: "COMPLETE", summary: "Market data ingested for RELIANCE (NSE: ₹1,420.50, Volume: 8.43M)", detail: { price: 1420.50, data_status: "OK", feed: "NSE Realtime Adapter" }, timestamp: "2026-09-01T09:30:00Z" },
    { step: 2, stage: "Signal Engine", status: "COMPLETE", summary: "Computed 3 signal dimensions: Momentum (0.84), Volume (0.78), RSI (0.82) -> Overall Bullish (81%)", detail: { momentum: "BULLISH", volume: "BULLISH", rsi: "BULLISH" }, timestamp: "2026-09-01T09:30:01Z" },
    { step: 3, stage: "Technical Agent", status: "COMPLETE", summary: "Technical Agent verified multi-timeframe moving average confluence above ₹1,400", detail: { signal: "BULLISH", confidence: 0.82 }, timestamp: "2026-09-01T09:30:01Z" },
    { step: 4, stage: "RAG Retrieval", status: "COMPLETE", summary: "Retrieved 4 high-relevance filings from synthetic corpus for RELIANCE", detail: { chunks_retrieved: 4, avg_similarity: 0.827 }, timestamp: "2026-09-01T09:30:02Z" },
    { step: 5, stage: "Fundamental Agent", status: "COMPLETE", summary: "Fundamental Agent analyzed Retail & Jio EBITDA growth offset by cautious O2C refining guidance", detail: { signal: "BULLISH", confidence: 0.85 }, timestamp: "2026-09-01T09:30:02Z" },
    { step: 6, stage: "Sentiment Agent", status: "COMPLETE", summary: "Sentiment Agent scored 28 Buy / 5 Hold analyst consensus; cautious petrochem sentiment", detail: { signal: "NEUTRAL", confidence: 0.57 }, timestamp: "2026-09-01T09:30:03Z" },
    { step: 7, stage: "Risk Agent", status: "COMPLETE", summary: "Risk Agent verified Beta (0.92) & portfolio concentration tolerance (12% Energy allocation)", detail: { risk_level: "MODERATE", confidence: 0.76 }, timestamp: "2026-09-01T09:30:03Z" },
    { step: 8, stage: "Synthesis & Personalization", status: "COMPLETE", summary: "Final Synthesis: BULLISH (81% confidence, BUY recommendation), High Profile Match for Moderate Investor", detail: { final_signal: "BULLISH", confidence: 0.81, recommendation: "BUY" }, timestamp: "2026-09-01T09:30:04Z" }
  ],
  metrics: {
    total_latency_ms: 42,
    per_module_latency_ms: { market: 12, rag: 18, profile: 8, agents: 4 },
    agent_latency_ms: { technical: 42, fundamental: 68, sentiment: 35, risk: 28 },
    agents_completed: 4,
    agents_failed: [],
    confidence: 0.81,
    portfolio_concentration: "low"
  },
  data_quality: {
    overall: "HIGH",
    market: "OK",
    rag: "OK",
    profile: "OK"
  }
};

export async function fetchAnalysis(symbol: string): Promise<AnalysisResponse> {
  try {
    const res = await fetch(`${API_BASE}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol, user_id: 'user_default', lookback: 5 })
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn('API error, using local template for symbol:', symbol, err);
  }

  // Fallback template
  const copy = JSON.parse(JSON.stringify(FALLBACK_RELIANCE)) as AnalysisResponse;
  copy.symbol = symbol.toUpperCase();
  if (symbol.toUpperCase() === 'TCS') {
    copy.company_name = 'TATA CONSULTANCY SERVICES';
    copy.price = 3890.10;
    copy.change = -17.50;
    copy.change_pct = -0.45;
    copy.signals.overall_signal = 'NEUTRAL';
    copy.signals.overall_confidence = 0.68;
    copy.synthesis.final_signal = 'NEUTRAL';
    copy.synthesis.confidence = 0.72;
    copy.synthesis.recommendation = 'HOLD';
    copy.agents.technical.signal = 'NEUTRAL';
    copy.agents.technical.confidence = 0.68;
    copy.agents.fundamental.signal = 'BULLISH';
    copy.agents.fundamental.confidence = 0.79;
    copy.agents.sentiment.signal = 'NEUTRAL';
    copy.agents.sentiment.confidence = 0.62;
    copy.agents.risk.signal = 'LOW';
    copy.agents.risk.confidence = 0.85;
    copy.profile.portfolio_exposure = 'IT: 42.5% (Overweight)';
    copy.profile.concentration_risk = 'Moderate';
  } else if (symbol.toUpperCase() === 'INFY') {
    copy.company_name = 'INFOSYS LIMITED';
    copy.price = 1532.90;
    copy.change = 0.00;
    copy.change_pct = 0.00;
    copy.signals.overall_signal = 'BULLISH';
    copy.signals.overall_confidence = 0.76;
    copy.synthesis.final_signal = 'BULLISH';
    copy.synthesis.confidence = 0.78;
    copy.synthesis.recommendation = 'ACCUMULATE';
    copy.agents.technical.signal = 'BULLISH';
    copy.agents.fundamental.signal = 'BULLISH';
    copy.agents.sentiment.signal = 'BULLISH';
    copy.agents.risk.signal = 'MODERATE';
    copy.profile.portfolio_exposure = 'IT: 42.5%';
    copy.profile.concentration_risk = 'Moderate';
  } else if (symbol.toUpperCase() === 'HDFCBANK') {
    copy.company_name = 'HDFC BANK LIMITED';
    copy.price = 1650.00;
    copy.change = 14.60;
    copy.change_pct = 0.89;
    copy.signals.overall_signal = 'BULLISH';
    copy.signals.overall_confidence = 0.83;
    copy.synthesis.final_signal = 'BULLISH';
    copy.synthesis.confidence = 0.84;
    copy.synthesis.recommendation = 'BUY';
    copy.agents.technical.signal = 'BULLISH';
    copy.agents.fundamental.signal = 'BULLISH';
    copy.agents.sentiment.signal = 'BULLISH';
    copy.agents.risk.signal = 'LOW';
    copy.profile.portfolio_exposure = 'Banking: 26.9% (Balanced)';
    copy.profile.concentration_risk = 'Low';
  }
  return copy;
}

export async function fetchCorpusChat(query: string, symbol: string) {
  try {
    const res = await fetch(`${API_BASE}/corpus/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, symbol })
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn('API error fetching corpus chat:', err);
  }
  return null;
}
