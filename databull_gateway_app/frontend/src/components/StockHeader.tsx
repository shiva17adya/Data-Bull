import React from 'react';
import { TrendingUp, TrendingDown, Clock, ShieldCheck } from 'lucide-react';
import { AnalysisResponse } from '../types';

interface StockHeaderProps {
  data: AnalysisResponse;
  timeframe: string;
  setTimeframe: (tf: string) => void;
}

export const StockHeader: React.FC<StockHeaderProps> = ({
  data,
  timeframe,
  setTimeframe,
}) => {
  const isPositive = data.change >= 0;

  return (
    <div className="flex flex-col md:flex-row md:items-center justify-between pb-3 border-b border-[#1C2638] gap-4">
      {/* Left info */}
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-2.5">
          <h1 className="text-xl font-extrabold text-white tracking-tight">
            {data.company_name}
          </h1>
          <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded bg-[#162234] text-cyan-300 border border-[#253A56]">
            {data.symbol} : {data.exchange}
          </span>
          <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-800/60 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            {data.market_status}
          </span>
        </div>

        <div className="flex items-baseline gap-3">
          <span className="text-2xl font-black text-white font-mono tracking-tight">
            ₹{data.price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
          <span
            className={`text-sm font-mono font-bold flex items-center gap-1 ${
              isPositive ? 'text-emerald-400' : 'text-rose-400'
            }`}
          >
            {isPositive ? '+' : ''}
            {data.change.toFixed(2)} ({isPositive ? '+' : ''}{data.change_pct.toFixed(2)}%)
            {isPositive ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
          </span>
          <span className="text-[11px] text-slate-500 font-mono flex items-center gap-1">
            <Clock className="w-3 h-3 text-slate-500" />
            As of Live Feed
          </span>
        </div>
      </div>

      {/* Right: Timeframe selectors & Data Quality */}
      <div className="flex items-center space-x-3">
        <div className="flex items-center bg-[#0E1522] p-0.5 rounded-md border border-[#1C2638]">
          {['1D', '1W', '1M', 'YTD'].map((tf) => {
            const active = timeframe === tf;
            return (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={`px-2.5 py-1 text-[11px] font-mono font-semibold rounded transition-all cursor-pointer ${
                  active
                    ? 'bg-[#1D2B40] text-cyan-300 shadow-sm border border-[#2B4160]'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {tf}
              </button>
            );
          })}
        </div>

        <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#0D1624] border border-[#1B2B42] text-[11px] text-cyan-400 font-mono">
          <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
          <span>Feed: {data.data_quality.overall} Quality</span>
        </div>
      </div>
    </div>
  );
};
