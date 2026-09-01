import React from 'react';

interface FooterStatusBarProps {
  latencyMs: number;
}

export const FooterStatusBar: React.FC<FooterStatusBarProps> = ({ latencyMs }) => {
  return (
    <footer className="h-7 border-t border-[#1C2638] bg-[#070A10] px-4 flex items-center justify-between text-[11px] font-mono text-slate-400 select-none">
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-1.5">
          <span className="text-slate-500">System Status:</span>
          <span>Market Data</span>
          <span className="text-emerald-400 font-bold">[OK]</span>
        </div>

        <span className="text-slate-600">|</span>

        <div className="flex items-center space-x-1.5">
          <span>Document Corpus</span>
          <span className="text-cyan-400 font-bold">[SYNC]</span>
        </div>

        <span className="text-slate-600">|</span>

        <div className="flex items-center space-x-1.5">
          <span>Agents</span>
          <span className="text-emerald-400 font-bold">[4/4 READY]</span>
        </div>
      </div>

      <div className="flex items-center space-x-3 text-slate-500">
        <span>Latency: <strong className="text-cyan-400">{latencyMs.toFixed(1)}ms</strong></span>
        <span className="text-slate-600">|</span>
        <span className="text-slate-400 hover:text-slate-200 cursor-pointer">Privacy</span>
        <span className="text-slate-400 hover:text-slate-200 cursor-pointer">Terms</span>
        <span className="text-slate-400 hover:text-slate-200 cursor-pointer">Support</span>
      </div>
    </footer>
  );
};
