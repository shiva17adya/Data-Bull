import React, { useState } from 'react';
import { X, CheckCircle, AlertTriangle, ChevronRight, FileText, Cpu, Scale, Shield, Sparkles } from 'lucide-react';
import { AnalysisResponse } from '../types';

interface WhyThisResultModalProps {
  isOpen: boolean;
  onClose: () => void;
  data: AnalysisResponse;
}

export const WhyThisResultModal: React.FC<WhyThisResultModalProps> = ({
  isOpen,
  onClose,
  data,
}) => {
  if (!isOpen) return null;

  const [activeTab, setActiveTab] = useState<'trace' | 'factors' | 'evidence' | 'agents'>('trace');
  const { synthesis, agents, evidence, reasoning_trace } = data;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="bg-[#0D131F] border border-[#23354E] rounded-xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden font-sans">
        {/* Modal Header */}
        <div className="p-4 border-b border-[#1C2638] bg-[#090E17] flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded bg-cyan-950/80 border border-cyan-700/60 flex items-center justify-center text-cyan-400">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-bold text-white uppercase tracking-wider">
                  Decision Intelligence & Explainability Trace
                </h2>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#162234] text-cyan-300 border border-[#253A56]">
                  {data.symbol} : {data.exchange}
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono">
                Full cryptographic agent consensus trace and verifiable RAG attribution
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-md hover:bg-[#162030] text-slate-400 hover:text-white transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Highlight Banner */}
        <div className="bg-[#0A101A] border-b border-[#1C2638] px-4 py-3 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div>
              <span className="text-[10px] text-slate-500 font-mono block">FINAL SYNTHESIS</span>
              <span className="text-base font-black font-mono text-emerald-400 tracking-wide">
                {synthesis.final_signal} ({Math.round(synthesis.confidence * 100)}% CONFIDENCE)
              </span>
            </div>
            <div className="border-l border-[#1C2638] pl-4">
              <span className="text-[10px] text-slate-500 font-mono block">RECOMMENDATION</span>
              <span className="text-sm font-bold text-white font-mono">{synthesis.recommendation}</span>
            </div>
            <div className="border-l border-[#1C2638] pl-4">
              <span className="text-[10px] text-slate-500 font-mono block">RISK POSTURE</span>
              <span className="text-sm font-bold text-cyan-400 font-mono">{synthesis.risk_level} RISK</span>
            </div>
          </div>

          {/* Tab buttons */}
          <div className="flex items-center space-x-1 bg-[#101826] p-1 rounded-lg border border-[#1E2B3E]">
            {(['trace', 'factors', 'evidence', 'agents'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-3 py-1 text-xs font-mono font-semibold rounded uppercase transition-all cursor-pointer ${
                  activeTab === tab
                    ? 'bg-cyan-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {/* TAB 1: DECISION REASONING TRACE (8-STAGE PIPELINE) */}
          {activeTab === 'trace' && (
            <div className="space-y-3">
              <div className="text-xs font-mono font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center justify-between">
                <span>Autonomous Multi-Stage Pipeline Execution</span>
                <span className="text-emerald-400">Total Latency: {data.metrics.total_latency_ms}ms</span>
              </div>

              <div className="relative border-l-2 border-[#1E2C40] ml-4 space-y-4 py-2">
                {reasoning_trace.map((step) => (
                  <div key={step.step} className="relative pl-6">
                    <div className="absolute -left-[9px] top-1 w-4 h-4 rounded-full bg-[#0E1726] border-2 border-emerald-400 flex items-center justify-center">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                    </div>

                    <div className="p-3 rounded-lg bg-[#090E17] border border-[#192436] flex flex-col gap-1">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono font-bold text-cyan-300">
                            STEP {step.step}: {step.stage}
                          </span>
                          <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-emerald-950 text-emerald-400 border border-emerald-800/50">
                            {step.status}
                          </span>
                        </div>
                        <span className="text-[10px] font-mono text-slate-500">{step.timestamp}</span>
                      </div>
                      <p className="text-xs text-slate-300 font-sans">{step.summary}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 2: SUPPORTING FACTORS & COUNTER-SIGNALS */}
          {activeTab === 'factors' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Supporting Factors */}
              <div className="p-4 rounded-lg bg-[#081512] border border-emerald-900/50 flex flex-col gap-2">
                <div className="flex items-center space-x-2 text-emerald-400 font-mono text-xs font-bold uppercase tracking-wider">
                  <CheckCircle className="w-4 h-4" />
                  <span>Primary Supporting Factors</span>
                </div>
                <ul className="space-y-2 text-xs text-slate-300">
                  {synthesis.supporting_factors.map((factor, i) => (
                    <li key={i} className="flex items-start gap-2 bg-[#05110E] p-2.5 rounded border border-emerald-950">
                      <span className="text-emerald-400 font-mono font-bold">+{i + 1}</span>
                      <span>{factor}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Counter-signals */}
              <div className="p-4 rounded-lg bg-[#180C10] border border-rose-900/50 flex flex-col gap-2">
                <div className="flex items-center space-x-2 text-rose-400 font-mono text-xs font-bold uppercase tracking-wider">
                  <AlertTriangle className="w-4 h-4" />
                  <span>Counter-Signals & Risk Mitigants</span>
                </div>
                <ul className="space-y-2 text-xs text-slate-300">
                  {synthesis.counter_signals.map((counter, i) => (
                    <li key={i} className="flex items-start gap-2 bg-[#12070A] p-2.5 rounded border border-rose-950">
                      <span className="text-rose-400 font-mono font-bold">!{i + 1}</span>
                      <span>{counter}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* TAB 3: VERIFIABLE RAG ATTRIBUTION */}
          {activeTab === 'evidence' && (
            <div className="space-y-3">
              <div className="text-xs font-mono font-bold text-slate-400 uppercase tracking-wider flex items-center justify-between">
                <span>Retrieved Filings & Verified Ground Truth</span>
                <span className="text-cyan-400 font-mono">{evidence.length} Evidence Chunks Cited</span>
              </div>

              <div className="space-y-3">
                {evidence.map((chunk) => (
                  <div key={chunk.chunk_id} className="p-3.5 rounded-lg bg-[#090E17] border border-[#192436] flex flex-col gap-2">
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#141C2B] pb-2">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded bg-cyan-950/80 text-cyan-300 border border-cyan-800/60 font-mono text-[11px] font-bold">
                          {chunk.chunk_id}
                        </span>
                        <span className="text-xs font-bold text-slate-200">{chunk.source.title}</span>
                      </div>
                      <div className="flex items-center gap-2 text-[10px] font-mono text-slate-400">
                        <span className="px-1.5 py-0.5 rounded bg-[#131A27]">{chunk.source.section}</span>
                        <span className="px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400">
                          Relevance: {Math.round(chunk.similarity_score * 100)}%
                        </span>
                      </div>
                    </div>

                    <p className="text-xs text-slate-300 leading-relaxed italic bg-[#060910] p-2.5 rounded border border-[#101724]">
                      "{chunk.text}"
                    </p>

                    <div className="flex flex-wrap items-center justify-between text-[10px] font-mono text-slate-500 pt-1">
                      <span>Source: {chunk.source.source_name} | Type: <strong className="text-amber-300">{chunk.source.source_type}</strong></span>
                      <span>Published: {chunk.source.published_date}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 4: AGENT BREAKDOWN */}
          {activeTab === 'agents' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {Object.values(agents).map((agent) => (
                <div key={agent.agent} className="p-3.5 rounded-lg bg-[#090E17] border border-[#192436] flex flex-col gap-2">
                  <div className="flex items-center justify-between border-b border-[#141C2B] pb-1.5">
                    <span className="text-xs font-bold uppercase font-mono text-slate-200">{agent.agent} Agent</span>
                    <span className="text-xs font-mono font-extrabold text-emerald-400">{agent.signal} ({Math.round(agent.confidence * 100)}%)</span>
                  </div>
                  <ul className="text-xs text-slate-300 space-y-1">
                    {agent.reasoning.map((r, idx) => (
                      <li key={idx} className="leading-relaxed text-slate-300">• {r}</li>
                    ))}
                  </ul>
                  <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 pt-1 border-t border-[#141C2B]">
                    <span>Latency: {agent.latency_ms}ms</span>
                    <span>Quality: {agent.data_quality}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-3 border-t border-[#1C2638] bg-[#090E17] flex items-center justify-between">
          <span className="text-[11px] font-mono text-slate-400">
            Source Ground Truth Integrity: <strong className="text-emerald-400">VERIFIED & ACCREDITED</strong>
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded bg-[#162234] hover:bg-[#1E3048] text-white text-xs font-mono font-bold transition-all cursor-pointer"
          >
            Close Trace
          </button>
        </div>
      </div>
    </div>
  );
};
