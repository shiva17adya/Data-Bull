import React from 'react';
import { TrendingUp, TrendingDown, Minus, Bookmark } from 'lucide-react';

interface WatchlistItem {
  symbol: string;
  name: string;
  price: string;
  change: string;
  isPositive: boolean | null;
}

const WATCHLIST_ITEMS: WatchlistItem[] = [
  {
    symbol: 'RELIANCE',
    name: 'Reliance Ind.',
    price: '₹1,420.50',
    change: '+2.84%',
    isPositive: true,
  },
  {
    symbol: 'TCS',
    name: 'Tata Consultancy',
    price: '₹3,890.10',
    change: '-0.45%',
    isPositive: false,
  },
  {
    symbol: 'INFY',
    name: 'Infosys Ltd.',
    price: '₹1,532.90',
    change: '0.00%',
    isPositive: null,
  },
  {
    symbol: 'HDFCBANK',
    name: 'HDFC Bank Ltd.',
    price: '₹1,650.00',
    change: '+0.89%',
    isPositive: true,
  },
];

interface WatchlistSidebarProps {
  currentSymbol: string;
  onSelectSymbol: (symbol: string) => void;
}

export const WatchlistSidebar: React.FC<WatchlistSidebarProps> = ({
  currentSymbol,
  onSelectSymbol,
}) => {
  return (
    <aside className="w-52 border-r border-[#1C2638] bg-[#0A0E17] flex flex-col shrink-0 select-none">
      <div className="p-3 border-b border-[#1C2638] flex items-center justify-between">
        <div className="flex items-center space-x-1.5 text-xs font-semibold text-slate-300 tracking-wider uppercase">
          <Bookmark className="w-3.5 h-3.5 text-cyan-400" />
          <span>Watchlist</span>
        </div>
        <span className="text-[10px] text-slate-500 font-mono">LIVE TICKERS</span>
      </div>

      <div className="flex-1 overflow-y-auto divide-y divide-[#141C2B]">
        {WATCHLIST_ITEMS.map((item) => {
          const isSelected = currentSymbol.toUpperCase() === item.symbol;
          return (
            <button
              key={item.symbol}
              onClick={() => onSelectSymbol(item.symbol)}
              className={`w-full text-left p-3 transition-colors flex flex-col gap-1 cursor-pointer ${
                isSelected
                  ? 'bg-[#121A28] border-l-2 border-cyan-400'
                  : 'hover:bg-[#0E1522] border-l-2 border-transparent'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className={`text-xs font-bold font-mono ${isSelected ? 'text-white' : 'text-slate-200'}`}>
                  {item.symbol}
                </span>
                <span
                  className={`text-[11px] font-mono font-medium flex items-center gap-0.5 ${
                    item.isPositive === true
                      ? 'text-emerald-400'
                      : item.isPositive === false
                      ? 'text-rose-400'
                      : 'text-slate-400'
                  }`}
                >
                  {item.isPositive === true && <TrendingUp className="w-3 h-3" />}
                  {item.isPositive === false && <TrendingDown className="w-3 h-3" />}
                  {item.isPositive === null && <Minus className="w-3 h-3" />}
                  {item.change}
                </span>
              </div>

              <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
                <span>{item.price}</span>
              </div>
            </button>
          );
        })}
      </div>
    </aside>
  );
};
