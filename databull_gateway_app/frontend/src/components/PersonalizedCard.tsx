import React from 'react';
import { UserCheck, ShieldCheck, PieChart, Clock } from 'lucide-react';
import { AnalysisResponse } from '../types';

interface PersonalizedCardProps {
  data: AnalysisResponse;
}

export const PersonalizedCard: React.FC<PersonalizedCardProps> = ({ data }) => {
  const { profile, synthesis } = data;

  return (
    <div className="terminal-card p-4 flex flex-col justify-between bg-[#0C131F] border border-[#1C283B]">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#1C2638] pb-2.5">
        <div className="flex items-center space-x-2">
          <UserCheck className="w-3.5 h-3.5 text-emerald-400" />
          <span className="text-[11px] font-mono font-bold tracking-wider uppercase text-slate-300">
            Personalized Intelligence
          </span>
        </div>

        <span className="px-2 py-0.5 rounded bg-emerald-950/80 border border-emerald-700/60 text-emerald-400 text-[10px] font-mono font-bold flex items-center gap-1">
          <ShieldCheck className="w-3 h-3" />
          {profile.profile_match} PROFILE MATCH
        </span>
      </div>

      {/* Grid of Profile Metrics */}
      <div className="grid grid-cols-2 gap-2.5 my-3 text-xs font-mono">
        <div className="p-2 rounded bg-[#090E17] border border-[#162234]">
          <span className="text-[10px] text-slate-500 block">RISK TOLERANCE</span>
          <span className="text-slate-200 font-bold text-xs">{profile.risk_tolerance}</span>
        </div>

        <div className="p-2 rounded bg-[#090E17] border border-[#162234]">
          <span className="text-[10px] text-slate-500 block">HORIZON</span>
          <span className="text-slate-200 font-bold text-xs">{profile.horizon_label} ({profile.investment_horizon_years}Y)</span>
        </div>

        <div className="p-2 rounded bg-[#090E17] border border-[#162234]">
          <span className="text-[10px] text-slate-500 block">PORTFOLIO EXPOSURE</span>
          <span className="text-cyan-300 font-bold text-xs">{profile.portfolio_exposure}</span>
        </div>

        <div className="p-2 rounded bg-[#090E17] border border-[#162234]">
          <span className="text-[10px] text-slate-500 block">CONCENTRATION RISK</span>
          <span className="text-emerald-400 font-bold text-xs">{profile.concentration_risk}</span>
        </div>
      </div>

      {/* Reasoning narrative */}
      <div className="pt-2 border-t border-[#1C2638] text-[11px] text-slate-300 leading-relaxed font-sans">
        {synthesis.reasoning.map((line, idx) => (
          <p key={idx} className="mb-1 text-slate-300 last:mb-0">
            {line}
          </p>
        ))}
      </div>
    </div>
  );
};
