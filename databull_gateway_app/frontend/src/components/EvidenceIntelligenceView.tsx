import React, { useState } from 'react';
import { Bot, Send, Search, FileText, CheckCircle2, RefreshCw, Plus, ThumbsUp, ThumbsDown, Sparkles } from 'lucide-react';
import { WatchlistSidebar } from './WatchlistSidebar';

interface EvidenceIntelligenceViewProps {
  currentSymbol: string;
  onSelectSymbol: (sym: string) => void;
}

export const EvidenceIntelligenceView: React.FC<EvidenceIntelligenceViewProps> = ({
  currentSymbol,
  onSelectSymbol,
}) => {
  const [selectedCitation, setSelectedCitation] = useState<string>('SRC-01');
  const [chatInput, setChatInput] = useState<string>('');

  const citationsData: Record<string, {
    title: string;
    source_type: string;
    published_date: string;
    section: string;
    confidence_label: string;
    excerpt: string;
    entities: string[];
    sentiment: string;
  }> = {
    'SRC-01': {
      title: 'RELIANCE_Q3_FY24_Earnings_Transcript.pdf',
      source_type: 'Earnings Transcript',
      published_date: 'Jan 19, 2024',
      section: 'Management Commentary, pg 14',
      confidence_label: 'High (79%)',
      excerpt: 'Moving to the O2C segment, while we saw some stabilization in fuel cracks towards the end of the quarter, the overall margin environment remains challenging. Global macroeconomic headwinds, coupled with the influx of new capacity additions in China, are expected to cap any significant upside potential in the near term. Our forward guidance remains cautious, and our primary focus will be on maximizing downstream integration and optimizing feedstocks to defend our margins against these external pressures.',
      entities: ['Reliance O2C', 'China', 'Feedstocks'],
      sentiment: 'Cautious'
    },
    'SRC-02': {
      title: 'JPM_Initiation_Report_2024.pdf',
      source_type: 'Analyst Note',
      published_date: 'Jan 20, 2024',
      section: 'Energy & Petrochemicals, pg 8',
      confidence_label: 'High (84%)',
      excerpt: 'Analyst notes from JP Morgan emphasized the resilience in polymer spreads and downstream integration mitigating weak bulk commodity crack spreads.',
      entities: ['JP Morgan', 'Polymer Spreads'],
      sentiment: 'Constructive'
    },
    'SRC-03': {
      title: 'SEC_10Q_Reliance_Equivalent_Q3.pdf',
      source_type: 'SEC Filing',
      published_date: 'Dec 31, 2023',
      section: 'Segment Operations, pg 19',
      confidence_label: 'High (91%)',
      excerpt: 'Global capacity additions in Northeast Asia continue to compress regional crack spreads, requiring ongoing operational optimization.',
      entities: ['Northeast Asia', 'Regional Spreads'],
      sentiment: 'Neutral'
    }
  };

  const activeDetail = citationsData[selectedCitation] || citationsData['SRC-01'];

  return (
    <div className="flex-1 flex overflow-hidden bg-[#07090E]">
      {/* Left Sidebar */}
      <WatchlistSidebar currentSymbol={currentSymbol} onSelectSymbol={onSelectSymbol} />

      {/* Main Evidence Layout: 2 Columns (Chat/Q&A Center + Corpus Detail Right) */}
      <div className="flex-1 flex flex-col md:flex-row overflow-hidden divide-y md:divide-y-0 md:divide-x divide-[#1C2638]">
        {/* Center Panel: Intelligence Chat */}
        <div className="flex-1 flex flex-col justify-between bg-[#0A0E17] overflow-hidden">
          {/* Chat Header */}
          <div className="p-3 border-b border-[#1C2638] flex items-center justify-between bg-[#0B101A]">
            <div className="flex items-center space-x-2">
              <Bot className="w-4 h-4 text-cyan-400" />
              <span className="text-xs font-bold text-slate-200 tracking-wider uppercase font-mono">
                Intelligence Chat
              </span>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#162234] text-cyan-300 border border-[#23354E]">
              Model: Agent-X v2.4
            </span>
          </div>

          {/* Context Banner */}
          <div className="px-4 py-2 bg-[#0E1522] border-b border-[#182335] text-[11px] font-mono text-slate-400 flex items-center justify-between">
            <span>Context Established: <strong className="text-cyan-300">{currentSymbol} Industries</strong> (500 Segment)</span>
            <span className="text-emerald-400 font-semibold flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> Live RAG Ingest
            </span>
          </div>

          {/* Chat Messages Stream */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 font-sans text-xs">
            {/* User Question */}
            <div className="flex justify-end">
              <div className="bg-[#182436] border border-[#2A3C56] text-slate-100 rounded-2xl rounded-tr-sm px-4 py-2.5 max-w-xl shadow-md">
                What is the consensus on Reliance's O2C margin outlook across the last 3 quarters?
                <div className="text-[9px] text-slate-400 text-right mt-1 font-mono">10:42 AM</div>
              </div>
            </div>

            {/* Assistant AI Multi-Agent Synthesis */}
            <div className="flex items-start space-x-3 max-w-2xl">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-cyan-600 to-blue-600 flex items-center justify-center text-white shrink-0 shadow-md shadow-cyan-900/40">
                <Sparkles className="w-4 h-4" />
              </div>

              <div className="bg-[#0E1624] border border-[#1E2E44] rounded-2xl rounded-tl-sm p-4 text-slate-200 space-y-3 shadow-xl">
                <p className="leading-relaxed text-slate-200">
                  The consensus on Reliance Industries' Oil-to-Chemicals (O2C) margin outlook over the last three quarters suggests a highly volatile environment transitioning into cautious stabilization. Analysis of the corpus indicates three distinct phases:
                </p>

                <div className="space-y-2.5 pl-2 border-l-2 border-cyan-500/40">
                  <div>
                    <strong className="text-cyan-300 font-mono block mb-0.5">• Q1 (Significant Contraction):</strong>
                    <span className="text-slate-300">
                      Margins were severely impacted by planned shutdowns at the Jamnagar complex and narrowed gasoil cracks. Earnings reports highlight a drop in EBITDA margins by ~210 bps QoQ.
                    </span>{' '}
                    <button
                      onClick={() => setSelectedCitation('SRC-01')}
                      className="inline-flex items-center px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-700/60 font-mono text-[10px] font-bold cursor-pointer hover:bg-cyan-900 transition-colors"
                    >
                      [SRC-01]
                    </button>
                  </div>

                  <div>
                    <strong className="text-cyan-300 font-mono block mb-0.5">• Q2 (Partial Recovery):</strong>
                    <span className="text-slate-300">
                      Driven by improved domestic demand and optimized feedstock sourcing (advantageous crude procurement), margins saw a sequential recovery, though still below historical averages. Analyst notes from JP Morgan emphasized the resilience in polymer spreads.
                    </span>{' '}
                    <button
                      onClick={() => setSelectedCitation('SRC-02')}
                      className="inline-flex items-center px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-700/60 font-mono text-[10px] font-bold cursor-pointer hover:bg-cyan-900 transition-colors"
                    >
                      [SRC-02]
                    </button>
                  </div>

                  <div>
                    <strong className="text-cyan-300 font-mono block mb-0.5">• Q3 (Cautious Outlook):</strong>
                    <span className="text-slate-300">
                      Forward guidance remains muted. While fuel cracks have stabilized, global macroeconomic headwinds and new capacity additions in China are expected to cap upside potential. Management commentary stresses focus on downstream integration to defend margins.
                    </span>{' '}
                    <button
                      onClick={() => setSelectedCitation('SRC-03')}
                      className="inline-flex items-center px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-700/60 font-mono text-[10px] font-bold cursor-pointer hover:bg-cyan-900 transition-colors"
                    >
                      [SRC-03]
                    </button>
                  </div>
                </div>

                {/* Synthesis Metrics Box */}
                <div className="grid grid-cols-2 gap-2 pt-2 border-t border-[#1C2738]">
                  <div className="p-2 rounded bg-[#090F1A] border border-[#162335]">
                    <span className="text-[10px] text-slate-500 font-mono block">Avg O2C Est. Margin</span>
                    <span className="text-sm font-bold font-mono text-emerald-400">8.4%</span>
                  </div>
                  <div className="p-2 rounded bg-[#090F1A] border border-[#162335]">
                    <span className="text-[10px] text-slate-500 font-mono block">Sentiment Shift</span>
                    <span className="text-sm font-bold font-mono text-amber-400">Neutral-to-Bearish</span>
                  </div>
                </div>

                {/* Message footer */}
                <div className="flex items-center justify-between text-[10px] font-mono text-slate-400 pt-1">
                  <span className="flex items-center gap-1 text-emerald-400">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> Processed 4 documents in 1.2s
                  </span>
                  <div className="flex items-center space-x-2 text-slate-400">
                    <button className="hover:text-slate-200"><ThumbsUp className="w-3 h-3" /></button>
                    <button className="hover:text-slate-200"><ThumbsDown className="w-3 h-3" /></button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Chat Input Bar */}
          <div className="p-3 border-t border-[#1C2638] bg-[#0A0E17]">
            <div className="relative flex items-center">
              <FileText className="w-4 h-4 text-slate-500 absolute left-3" />
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="Ask the corpus or paste a document snippet..."
                className="w-full bg-[#0E1522] border border-[#1C2638] rounded-lg pl-9 pr-24 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500/60 font-mono"
              />
              <div className="absolute right-2 flex items-center space-x-2">
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#162030] text-cyan-400 border border-[#233145]">
                  Search: ON
                </span>
                <button className="p-1 rounded bg-cyan-600 hover:bg-cyan-500 text-white cursor-pointer transition-colors">
                  <Send className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
            <div className="text-[10px] text-slate-500 font-mono mt-1 text-center">
              Enter to send, Shift+Enter for new line
            </div>
          </div>
        </div>

        {/* Right Panel: Corpus Distribution & Evidence Detail */}
        <div className="w-full md:w-96 flex flex-col bg-[#090D15] overflow-y-auto divide-y divide-[#1C2638]">
          {/* Section 1: Corpus Distribution */}
          <div className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold font-mono uppercase tracking-wider text-slate-300">
                Corpus Distribution
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#162234] text-slate-400 border border-[#23354E]">
                1,142 Docs
              </span>
            </div>

            <div className="space-y-2 text-xs font-mono">
              <div>
                <div className="flex justify-between text-slate-400 mb-1 text-[11px]">
                  <span>SEC Filings</span>
                  <span>45%</span>
                </div>
                <div className="h-1.5 w-full bg-[#131B28] rounded-full overflow-hidden">
                  <div className="h-full bg-cyan-400 rounded-full" style={{ width: '45%' }}></div>
                </div>
              </div>

              <div>
                <div className="flex justify-between text-slate-400 mb-1 text-[11px]">
                  <span>Earnings Trs.</span>
                  <span>28%</span>
                </div>
                <div className="h-1.5 w-full bg-[#131B28] rounded-full overflow-hidden">
                  <div className="h-full bg-amber-400 rounded-full" style={{ width: '28%' }}></div>
                </div>
              </div>

              <div>
                <div className="flex justify-between text-slate-400 mb-1 text-[11px]">
                  <span>Analyst Notes</span>
                  <span>18%</span>
                </div>
                <div className="h-1.5 w-full bg-[#131B28] rounded-full overflow-hidden">
                  <div className="h-full bg-indigo-400 rounded-full" style={{ width: '18%' }}></div>
                </div>
              </div>

              <div>
                <div className="flex justify-between text-slate-400 mb-1 text-[11px]">
                  <span>News/Other</span>
                  <span>9%</span>
                </div>
                <div className="h-1.5 w-full bg-[#131B28] rounded-full overflow-hidden">
                  <div className="h-full bg-slate-500 rounded-full" style={{ width: '9%' }}></div>
                </div>
              </div>
            </div>

            {/* Document list */}
            <div className="pt-2 space-y-1.5 font-mono text-[11px]">
              <div className="p-2 rounded bg-[#0D1420] border border-[#1A2638] flex items-center justify-between">
                <div className="truncate mr-2 text-slate-300">RELIANCE_Q3_FY24</div>
                <span className="text-[9px] px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 font-bold">SYNCED</span>
              </div>
              <div className="p-2 rounded bg-[#0D1420] border border-[#1A2638] flex items-center justify-between">
                <div className="truncate mr-2 text-slate-300">JPM_Initiation_R...</div>
                <span className="text-[9px] px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 font-bold">SYNCED</span>
              </div>
              <div className="p-2 rounded bg-[#0D1420] border border-[#1A2638] flex items-center justify-between">
                <div className="truncate mr-2 text-slate-300">SEC_10Q_Reliance...</div>
                <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-950 text-amber-400 font-bold">INDEXING</span>
              </div>
            </div>
          </div>

          {/* Section 2: Selected Evidence Detail */}
          <div className="p-4 space-y-3 flex-1 flex flex-col justify-between">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <span className="px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-700/60 font-mono text-[11px] font-bold">
                    {selectedCitation}
                  </span>
                  <span className="text-xs font-bold font-mono text-slate-200">Evidence Detail</span>
                </div>

                <button className="flex items-center gap-1 px-2 py-1 rounded bg-[#16253B] hover:bg-[#1E3250] text-[10px] text-cyan-300 font-mono transition-colors cursor-pointer">
                  <Plus className="w-3 h-3" />
                  <span>Add to Analysis</span>
                </button>
              </div>

              {/* Document metadata table */}
              <div className="space-y-2 text-[11px] font-mono text-slate-400 bg-[#0C121D] p-3 rounded-lg border border-[#1A2638]">
                <div className="font-bold text-slate-200 truncate">{activeDetail.title}</div>
                <div className="grid grid-cols-2 gap-2 pt-1 border-t border-[#162030]">
                  <div>
                    <span className="text-[10px] text-slate-500 block">SOURCE TYPE</span>
                    <span className="text-slate-300">{activeDetail.source_type}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-500 block">PUBLISHED DATE</span>
                    <span className="text-slate-300">{activeDetail.published_date}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-500 block">SECTION / PAGE</span>
                    <span className="text-slate-300">{activeDetail.section}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-500 block">CONFIDENCE SCORE</span>
                    <span className="text-emerald-400 font-bold">{activeDetail.confidence_label}</span>
                  </div>
                </div>
              </div>

              {/* Exact excerpt */}
              <div className="space-y-1">
                <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500 block">
                  Exact Excerpt
                </span>
                <div className="p-3 rounded-lg bg-[#05080E] border border-[#151E2E] text-xs text-slate-300 leading-relaxed font-sans italic">
                  "{activeDetail.excerpt}"
                </div>
              </div>

              {/* Entities & Sentiment */}
              <div className="space-y-1.5">
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span className="text-[10px] font-mono text-slate-500">Entities:</span>
                  {activeDetail.entities.map((e, idx) => (
                    <span key={idx} className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#131C2A] text-slate-300 border border-[#202E42]">
                      {e}
                    </span>
                  ))}
                </div>

                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] font-mono text-slate-500">Sentiment:</span>
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-amber-950/80 text-amber-400 border border-amber-800/60">
                    {activeDetail.sentiment}
                  </span>
                </div>
              </div>
            </div>

            <div className="pt-2 text-[10px] font-mono text-slate-500 text-center">
              SOURCE TYPE: SYNTHETIC / DEMO CORPUS
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
