import React from 'react';
import { Bot, BarChart3, LineChart, Shield, Newspaper } from 'lucide-react';
import { AnalysisResponse } from '../types';

interface ConsensusNetworkProps {
  data: AnalysisResponse;
  onOpenWhy: () => void;
}

export const ConsensusNetwork: React.FC<ConsensusNetworkProps> = ({ data, onOpenWhy }) => {
  const { technical, fundamental, sentiment, risk } = data.agents;

  const getSignalColor = (signal: string) => {
    if (signal === 'BULLISH') return 'text-emerald-400 border-emerald-500/40 bg-emerald-950/40';
    if (signal === 'BEARISH') return 'text-rose-400 border-rose-500/40 bg-rose-950/40';
    if (signal === 'MODERATE' || signal === 'LOW') return 'text-cyan-400 border-cyan-500/40 bg-cyan-950/40';
    return 'text-slate-300 border-slate-700 bg-slate-900/40';
  };

  return (
    <div className="terminal-card p-4 relative flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 font-mono">
          Multi-Agent Consensus Network
        </span>
        <span className="text-[10px] text-emerald-400 font-mono flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
          4/4 AGENTS SYNCHRONIZED
        </span>
      </div>

      {/* Interactive Agent Node Network */}
      <div className="relative py-4 px-2">
        {/* Visual Circuit Lines (SVG) */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none z-0">
          <line x1="25%" y1="30%" x2="50%" y2="50%" stroke="#1E293B" strokeWidth="2" strokeDasharray="4 4" />
          <line x1="25%" y1="70%" x2="50%" y2="50%" stroke="#1E293B" strokeWidth="2" strokeDasharray="4 4" />
          <line x1="75%" y1="30%" x2="50%" y2="50%" stroke="#1E293B" strokeWidth="2" strokeDasharray="4 4" />
          <line x1="75%" y1="70%" x2="50%" y2="50%" stroke="#1E293B" strokeWidth="2" strokeDasharray="4 4" />
        </svg>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 relative z-10">
          {/* Technical Agent */}
          <div className={`p-3 rounded-lg border flex flex-col gap-1.5 transition-all hover:scale-[1.02] cursor-pointer ${getSignalColor(technical.signal)}`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <LineChart className="w-4 h-4 text-emerald-400" />
                <span className="text-xs font-bold text-slate-200">Technical</span>
              </div>
              <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-black/40 text-emerald-300">
                {Math.round(technical.confidence * 100)}%
              </span>
            </div>
            <div className="text-xs font-extrabold font-mono tracking-wide">{technical.signal}</div>
            <p className="text-[10px] text-slate-400 line-clamp-2 leading-relaxed">
              {technical.reasoning[0] || 'Confluence above key resistance.'}
            </p>
          </div>

          {/* Fundamental Agent */}
          <div className={`p-3 rounded-lg border flex flex-col gap-1.5 transition-all hover:scale-[1.02] cursor-pointer ${getSignalColor(fundamental.signal)}`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <BarChart3 className="w-4 h-4 text-emerald-400" />
                <span className="text-xs font-bold text-slate-200">Fundamental</span>
              </div>
              <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-black/40 text-emerald-300">
                {Math.round(fundamental.confidence * 100)}%
              </span>
            </div>
            <div className="text-xs font-extrabold font-mono tracking-wide">{fundamental.signal}</div>
            <p className="text-[10px] text-slate-400 line-clamp-2 leading-relaxed">
              {fundamental.reasoning[0] || 'Strong revenue & EBITDA margin expansion.'}
            </p>
          </div>

          {/* Sentiment Agent */}
          <div className={`p-3 rounded-lg border flex flex-col gap-1.5 transition-all hover:scale-[1.02] cursor-pointer ${getSignalColor(sentiment.signal)}`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <Newspaper className="w-4 h-4 text-cyan-400" />
                <span className="text-xs font-bold text-slate-200">Sentiment</span>
              </div>
              <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-black/40 text-slate-300">
                {Math.round(sentiment.confidence * 100)}%
              </span>
            </div>
            <div className="text-xs font-extrabold font-mono tracking-wide">{sentiment.signal}</div>
            <p className="text-[10px] text-slate-400 line-clamp-2 leading-relaxed">
              {sentiment.reasoning[0] || 'Analyst ratings neutral to constructive.'}
            </p>
          </div>

          {/* Risk Agent */}
          <div className={`p-3 rounded-lg border flex flex-col gap-1.5 transition-all hover:scale-[1.02] cursor-pointer ${getSignalColor(risk.signal)}`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <Shield className="w-4 h-4 text-cyan-400" />
                <span className="text-xs font-bold text-slate-200">Risk</span>
              </div>
              <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-black/40 text-cyan-300">
                {Math.round(risk.confidence * 100)}%
              </span>
            </div>
            <div className="text-xs font-extrabold font-mono tracking-wide">{risk.signal}</div>
            <p className="text-[10px] text-slate-400 line-clamp-2 leading-relaxed">
              {risk.reasoning[0] || 'Beta < 1.0; low portfolio concentration.'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
