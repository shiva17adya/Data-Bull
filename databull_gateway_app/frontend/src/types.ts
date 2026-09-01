export type SignalType = 'BULLISH' | 'MODERATELY_BULLISH' | 'NEUTRAL' | 'MODERATELY_BEARISH' | 'BEARISH' | 'UNAVAILABLE';
export type RecommendationType = 'BUY' | 'ACCUMULATE' | 'HOLD' | 'REDUCE' | 'SELL';
export type AgentStatus = 'success' | 'insufficient_data' | 'failed' | 'processing' | 'degraded';

export interface SourceAttribution {
  document_id: string;
  title: string;
  company: string;
  symbol: string;
  document_type: string;
  section: string;
  source_name: string;
  source_type: string;
  published_date: string;
  entities?: string[];
  sentiment?: string;
}

export interface EvidenceChunk {
  chunk_id: string;
  text: string;
  similarity_score: number;
  source: SourceAttribution;
}

export interface SignalDimension {
  name: string;
  signal: SignalType;
  value: number | null;
  confidence: number;
  evidence: string[];
}

export interface AgentOutput {
  agent: 'technical' | 'fundamental' | 'sentiment' | 'risk';
  status: AgentStatus;
  signal: SignalType | 'MODERATE' | 'LOW' | 'HIGH';
  confidence: number;
  reasoning: string[];
  evidence: { source: string; section: string; text: string; score: number }[];
  data_quality: 'HIGH' | 'MEDIUM' | 'LOW' | 'NONE';
  latency_ms: number;
  errors: string[];
}

export interface SynthesisData {
  final_signal: SignalType;
  confidence: number;
  recommendation: RecommendationType;
  directional_score: number;
  risk_level: 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';
  timeframe?: string;
  supporting_factors: string[];
  counter_signals: string[];
  risk_factors: string[];
  personalization: string[];
  reasoning: string[];
}

export interface ProfileData {
  user_id: string;
  risk_tolerance: string;
  investment_horizon_years: number;
  horizon_label: string;
  profile_match: string;
  portfolio_exposure: string;
  concentration_risk: string;
  personalization_factors: string[];
  personalization_guidance?: {
    risk_sensitivity: string;
    position_sensitivity: string;
    accumulation_bias: string;
  };
  is_watchlisted?: boolean;
}

export interface HoldingItem {
  symbol: string;
  quantity: number;
  average_price: number;
  current_price: number;
  value: number;
  position_percentage: number;
}

export interface PortfolioData {
  total_value: number;
  holdings: HoldingItem[];
  concentration_level?: string;
  top_3_concentration?: number;
  largest_position?: { symbol: string; percentage: number };
  risk_flags: string[];
}

export interface ReasoningTraceStep {
  step: number;
  stage: string;
  status: 'COMPLETE' | 'PROCESSING' | 'DEGRADED' | 'FAILED';
  summary: string;
  detail: Record<string, any>;
  timestamp: string;
}

export interface MetricsData {
  total_latency_ms: number;
  per_module_latency_ms: {
    market: number;
    rag: number;
    profile: number;
    agents: number;
  };
  agent_latency_ms: {
    technical: number;
    fundamental: number;
    sentiment: number;
    risk: number;
  };
  agents_completed: number;
  agents_failed: string[];
  confidence: number;
  portfolio_concentration?: string;
}

export interface DataQualityData {
  overall: 'HIGH' | 'MEDIUM' | 'LOW' | 'NONE';
  market: 'OK' | 'DEGRADED' | 'UNAVAILABLE';
  rag: 'OK' | 'NO_RESULTS' | 'DEGRADED';
  profile: 'OK' | 'MISSING';
}

export interface AnalysisResponse {
  symbol: string;
  company_name: string;
  exchange: string;
  price: number;
  change: number;
  change_pct: number;
  market_status: string;
  currency: string;
  ohlc: {
    open: number;
    high: number;
    low: number;
    close: number;
  };
  volume: number;
  signals: {
    price_momentum: SignalDimension;
    volume_anomaly: SignalDimension;
    rsi: SignalDimension;
    overall_signal: SignalType;
    overall_confidence: number;
  };
  agents: {
    technical: AgentOutput;
    fundamental: AgentOutput;
    sentiment: AgentOutput;
    risk: AgentOutput;
  };
  synthesis: SynthesisData;
  profile: ProfileData;
  portfolio: PortfolioData;
  evidence: EvidenceChunk[];
  reasoning_trace: ReasoningTraceStep[];
  metrics: MetricsData;
  data_quality: DataQualityData;
}

export interface CorpusDocument {
  document_id: string;
  title: string;
  company: string;
  symbol: string;
  document_type: string;
  source_name: string;
  source_type: string;
  published_date: string;
  status: 'SYNCED' | 'INDEXING' | 'ERROR';
  section: string;
  confidence_score: number;
  excerpt: string;
  entities: string[];
  sentiment: string;
}

export interface CitationItem {
  id: string;
  title: string;
  source_type: string;
  published_date: string;
  section: string;
  confidence_score: number;
  confidence_label: string;
  excerpt: string;
  entities: string[];
  sentiment: string;
}
