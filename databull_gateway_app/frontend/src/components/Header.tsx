import React from 'react';
import { Search, Bell, Settings, User, Activity, Zap } from 'lucide-react';

interface HeaderProps {
  activeTab: 'overview' | 'analysis' | 'portfolio' | 'evidence';
  setActiveTab: (tab: 'overview' | 'analysis' | 'portfolio' | 'evidence') => void;
  searchQuery: string;
  setSearchQuery: (q: string) => void;
  onSearchSubmit: (e: React.FormEvent) => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  searchQuery,
  setSearchQuery,
  onSearchSubmit
}) => {
  return (
    <header className="h-14 border-b border-[#1C2638] bg-[#0A0E17] px-4 flex items-center justify-between select-none sticky top-0 z-30">
      {/* Left: Brand & Navigation */}
      <div className="flex items-center space-x-6">
        <div className="flex items-center space-x-2 cursor-pointer" onClick={() => setActiveTab('analysis')}>
          <div className="w-8 h-8 rounded bg-gradient-to-tr from-emerald-500 to-cyan-500 flex items-center justify-center font-black text-black text-lg tracking-tighter shadow-lg shadow-emerald-500/20">
            DB
          </div>
          <span className="text-lg font-bold tracking-tight text-white flex items-center gap-1">
            DataBull <span className="text-[10px] text-cyan-400 font-mono font-medium px-1.5 py-0.5 bg-cyan-950/60 border border-cyan-800/50 rounded">PRO</span>
          </span>
        </div>

        <nav className="flex items-center space-x-1">
          {(['overview', 'analysis', 'portfolio', 'evidence'] as const).map((tab) => {
            const isActive = activeTab === tab;
            return (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-3 py-1.5 rounded text-xs font-semibold uppercase tracking-wider transition-all cursor-pointer ${
                  isActive
                    ? 'bg-[#162234] text-white border border-[#253954] shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-[#101724]'
                }`}
              >
                {tab}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Middle: Search input */}
      <div className="flex-1 max-w-md mx-6">
        <form onSubmit={onSearchSubmit} className="relative">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search entity, query (e.g. RELIANCE, TCS)..."
            className="w-full bg-[#0E1522] border border-[#1C2638] rounded-md pl-9 pr-12 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500/60 transition-all font-mono"
          />
          <span className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[10px] text-slate-500 bg-[#162030] px-1.5 py-0.5 rounded border border-[#233145] font-mono">
            ⌘K
          </span>
        </form>
      </div>

      {/* Right: System Health & Actions */}
      <div className="flex items-center space-x-3">
        <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-[#0A1D1A] border border-emerald-900/50 text-emerald-400 text-xs font-mono">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span className="font-semibold">System Health</span>
          <span className="text-[10px] font-bold px-1 bg-emerald-950/80 rounded border border-emerald-700/50">OK</span>
        </div>

        <div className="flex items-center space-x-1 text-slate-400 border-l border-[#1C2638] pl-3">
          <button className="p-1.5 hover:text-slate-200 hover:bg-[#151E2E] rounded transition-colors" title="Notifications">
            <Bell className="w-4 h-4" />
          </button>
          <button className="p-1.5 hover:text-slate-200 hover:bg-[#151E2E] rounded transition-colors" title="Settings">
            <Settings className="w-4 h-4" />
          </button>
          <button className="p-1.5 hover:text-slate-200 hover:bg-[#151E2E] rounded transition-colors" title="Profile">
            <div className="w-6 h-6 rounded-full bg-gradient-to-r from-blue-600 to-indigo-600 flex items-center justify-center text-[10px] font-bold text-white">
              RK
            </div>
          </button>
        </div>
      </div>
    </header>
  );
};
