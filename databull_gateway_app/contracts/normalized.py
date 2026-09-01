"""
Normalized data contracts for DataBull Member 5.
Directly implements MEMBER5_FRONTEND_CONTRACT.md.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class MarketOHLC(BaseModel):
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None

class MarketBlock(BaseModel):
    price: Optional[float] = None
    ohlc: Optional[MarketOHLC] = None
    volume: Optional[float] = None
    currency: Optional[str] = "INR"
    as_of: str
    data_status: str = "OK"  # OK | DEGRADED | UNAVAILABLE
    warnings: List[str] = Field(default_factory=list)

class SignalDimension(BaseModel):
    name: str
    signal: str  # BULLISH | NEUTRAL | BEARISH | UNAVAILABLE
    value: Optional[float] = None
    confidence: float
    evidence: List[str] = Field(default_factory=list)

class SignalsBlock(BaseModel):
    price_momentum: SignalDimension
    volume_anomaly: SignalDimension
    rsi: SignalDimension
    overall_signal: str  # BULLISH | NEUTRAL | BEARISH
    overall_confidence: float

class EvidenceItem(BaseModel):
    source: str
    section: str
    text: str
    score: float

class AgentOutput(BaseModel):
    agent: str  # technical | fundamental | sentiment | risk
    status: str  # success | insufficient_data | failed
    signal: str  # BULLISH | NEUTRAL | BEARISH | MODERATE | LOW | HIGH
    confidence: float
    reasoning: List[str] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    data_quality: str = "HIGH"  # HIGH | MEDIUM | LOW | NONE
    latency_ms: int = 0
    errors: List[str] = Field(default_factory=list)

class SynthesisBlock(BaseModel):
    final_signal: str  # BULLISH | MODERATELY_BULLISH | NEUTRAL | MODERATELY_BEARISH | BEARISH
    confidence: float
    recommendation: str  # BUY | ACCUMULATE | HOLD | REDUCE | SELL
    directional_score: float
    risk_level: str  # LOW | MODERATE | HIGH | CRITICAL
    timeframe: Optional[str] = "3-6M"
    supporting_factors: List[str] = Field(default_factory=list)
    counter_signals: List[str] = Field(default_factory=list)
    risk_factors: List[str] = Field(default_factory=list)
    personalization: List[str] = Field(default_factory=list)
    reasoning: List[str] = Field(default_factory=list)

class ProfileBlock(BaseModel):
    user_id: Optional[str] = None
    risk_tolerance: Optional[str] = None
    investment_horizon_years: Optional[int] = None
    horizon_label: Optional[str] = None
    profile_match: Optional[str] = "HIGH"
    portfolio_exposure: Optional[str] = None
    concentration_risk: Optional[str] = None
    personalization_factors: List[str] = Field(default_factory=list)
    personalization_guidance: Optional[Dict[str, Any]] = None
    is_watchlisted: Optional[bool] = None

class HoldingItem(BaseModel):
    symbol: str
    quantity: int
    average_price: float
    current_price: float
    value: float
    position_percentage: float

class PortfolioBlock(BaseModel):
    total_value: float = 0.0
    holdings: List[HoldingItem] = Field(default_factory=list)
    concentration_level: Optional[str] = None
    top_3_concentration: Optional[float] = None
    largest_position: Optional[Dict[str, Any]] = None
    risk_flags: List[str] = Field(default_factory=list)

class SourceAttribution(BaseModel):
    document_id: str
    title: str
    company: str
    symbol: str
    document_type: str
    section: str
    source_name: str
    source_type: str = "SYNTHETIC / DEMO CORPUS"
    published_date: str
    entities: List[str] = Field(default_factory=list)
    sentiment: Optional[str] = None

class EvidenceChunk(BaseModel):
    chunk_id: str
    text: str
    similarity_score: float
    source: SourceAttribution

class ReasoningTraceStep(BaseModel):
    step: int
    stage: str
    status: str = "COMPLETE"
    summary: str
    detail: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str

class MetricsBlock(BaseModel):
    total_latency_ms: int
    per_module_latency_ms: Dict[str, int]
    agent_latency_ms: Dict[str, int]
    agents_completed: int
    agents_failed: List[str] = Field(default_factory=list)
    confidence: float
    portfolio_concentration: Optional[str] = None

class DataQualityBlock(BaseModel):
    overall: str  # HIGH | MEDIUM | LOW | NONE
    market: str  # OK | DEGRADED | UNAVAILABLE
    rag: str  # OK | NO_RESULTS | DEGRADED
    profile: str  # OK | MISSING

class NormalizedAnalysisResponse(BaseModel):
    symbol: str
    company_name: str
    exchange: str = "NSE"
    price: float
    change: float
    change_pct: float
    market_status: str = "MARKET OPEN"
    currency: str = "INR"
    market: Optional[MarketBlock] = None
    signals: SignalsBlock
    agents: Dict[str, AgentOutput]
    synthesis: SynthesisBlock
    profile: ProfileBlock
    portfolio: PortfolioBlock
    evidence: List[EvidenceChunk]
    reasoning_trace: List[ReasoningTraceStep]
    metrics: MetricsBlock
    data_quality: DataQualityBlock
