import React from 'react';
import { HelpCircle, TrendingUp, Zap, Sparkles } from 'lucide-react';
import { AnalysisResponse } from '../types';

interface SynthesisCardProps {
  data: AnalysisResponse;
  onOpenWhy: () => void;
}

export const SynthesisCard: React.FC<SynthesisCardProps> = ({ data, onOpenWhy }) => {
  const { synthesis } = data;
  const isBullish = synthesis.final_signal.includes('BULLISH');

  return (
    <div className="terminal-card p-4 relative flex flex-col justify-between overflow-hidden bg-gradient-to-br from-[#0C1522] to-[#0A0E17] border border-[#1F2D42] shadow-xl">
      {/* Glow highlight */}
      <div className={`absolute -right-12 -top-12 w-36 h-36 rounded-full blur-3xl opacity-20 ${
        isBullish ? 'bg-emerald-500' : 'bg-rose-500'
      }`}></div>

      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#1C2638] pb-2.5">
        <div className="flex items-center space-x-2">
          <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
          <span className="text-[11px] font-mono font-bold tracking-wider uppercase text-slate-300">
            Synthesis / Final Intelligence
          </span>
        </div>

        <button
          onClick={onOpenWhy}
          className="flex items-center space-x-1 px-2.5 py-1 rounded bg-[#16253B] hover:bg-[#1D3250] text-cyan-300 border border-cyan-500/40 text-[11px] font-mono font-bold transition-all shadow-sm cursor-pointer hover:shadow-cyan-500/10"
        >
          <HelpCircle className="w-3 h-3 text-cyan-400" />
          <span>[ WHY THIS RESULT? ]</span>
        </button>
      </div>

      {/* Centerpiece Signal Badge */}
      <div className="my-5 flex flex-col items-center justify-center">
        <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-emerald-950/60 border border-emerald-500/50 shadow-lg shadow-emerald-950 mb-2">
          <TrendingUp className="w-7 h-7 text-emerald-400" />
        </div>
        <h2 className="text-2xl font-black font-mono tracking-wider text-emerald-400 uppercase">
          {synthesis.final_signal}
        </h2>
        <span className="text-xs font-mono font-semibold text-slate-400 mt-1">
          Recommendation: <strong className="text-white px-1.5 py-0.5 rounded bg-[#162030]">{synthesis.recommendation}</strong>
        </span>
      </div>

      {/* Footer Metrics */}
      <div className="pt-2 border-t border-[#1C2638] flex items-center justify-between text-xs font-mono">
        <div className="flex items-center space-x-1.5">
          <span className="text-slate-500">Confidence:</span>
          <span className="font-bold text-emerald-400 bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-800/60">
            {Math.round(synthesis.confidence * 100)}%
          </span>
        </div>

        <div className="flex items-center space-x-1.5">
          <span className="text-slate-500">Timeframe:</span>
          <span className="font-semibold text-slate-300">{synthesis.timeframe || '3-6M'}</span>
        </div>
      </div>
    </div>
  );
};
