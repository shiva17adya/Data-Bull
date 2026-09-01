import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { WatchlistSidebar } from './components/WatchlistSidebar';
import { StockHeader } from './components/StockHeader';
import { ChartSection } from './components/ChartSection';
import { ConsensusNetwork } from './components/ConsensusNetwork';
import { SynthesisCard } from './components/SynthesisCard';
import { PersonalizedCard } from './components/PersonalizedCard';
import { WhyThisResultModal } from './components/WhyThisResultModal';
import { EvidenceIntelligenceView } from './components/EvidenceIntelligenceView';
import { FooterStatusBar } from './components/FooterStatusBar';
import { fetchAnalysis } from './services/api';
import { AnalysisResponse } from './types';

export function App() {
  const [activeTab, setActiveTab] = useState<'overview' | 'analysis' | 'portfolio' | 'evidence'>('analysis');
  const [currentSymbol, setCurrentSymbol] = useState<string>('RELIANCE');
  const [timeframe, setTimeframe] = useState<string>('1M');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isWhyOpen, setIsWhyOpen] = useState<boolean>(false);
  const [data, setData] = useState<AnalysisResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const loadStockData = async (symbol: string) => {
    setIsLoading(true);
    try {
      const res = await fetchAnalysis(symbol);
      setData(res);
    } catch (err) {
      console.error('Failed to load stock data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadStockData(currentSymbol);
  }, [currentSymbol]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    const sym = searchQuery.trim().toUpperCase();
    setCurrentSymbol(sym);
    setSearchQuery('');
  };

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-[#07090E] text-slate-200">
      {/* Top Header */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        onSearchSubmit={handleSearchSubmit}
      />

      {/* Primary Content View */}
      {activeTab === 'evidence' ? (
        <EvidenceIntelligenceView
          currentSymbol={currentSymbol}
          onSelectSymbol={(sym) => setCurrentSymbol(sym)}
        />
      ) : (
        <div className="flex-1 flex overflow-hidden">
          {/* Watchlist Sidebar */}
          <WatchlistSidebar
            currentSymbol={currentSymbol}
            onSelectSymbol={(sym) => setCurrentSymbol(sym)}
          />

          {/* Main Dashboard Panel */}
          <main className="flex-1 overflow-y-auto p-4 flex flex-col gap-4 bg-[#0A0E17]">
            {data && (
              <>
                {/* Stock Details Header */}
                <StockHeader
                  data={data}
                  timeframe={timeframe}
                  setTimeframe={setTimeframe}
                />

                {/* Price & Indicator Chart */}
                <ChartSection data={data} timeframe={timeframe} />

                {/* Multi-Agent Consensus Node Graph */}
                <ConsensusNetwork
                  data={data}
                  onOpenWhy={() => setIsWhyOpen(true)}
                />

                {/* Bottom Row: Synthesis & Personalization */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  <SynthesisCard
                    data={data}
                    onOpenWhy={() => setIsWhyOpen(true)}
                  />
                  <PersonalizedCard data={data} />
                </div>
              </>
            )}
          </main>
        </div>
      )}

      {/* WHY THIS RESULT MODAL */}
      {data && (
        <WhyThisResultModal
          isOpen={isWhyOpen}
          onClose={() => setIsWhyOpen(false)}
          data={data}
        />
      )}

      {/* Footer Status Bar */}
      <FooterStatusBar latencyMs={data?.metrics.total_latency_ms || 4.2} />
    </div>
  );
}

export default App;
