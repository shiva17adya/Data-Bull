import React, { useState } from 'react';
import { AnalysisResponse } from '../types';

interface ChartSectionProps {
  data: AnalysisResponse;
  timeframe: string;
}

export const ChartSection: React.FC<ChartSectionProps> = ({ data, timeframe }) => {
  const [hoveredPoint, setHoveredPoint] = useState<number | null>(null);

  // Generate synthetic points based on ticker price
  const basePrice = data.price;
  const isPositive = data.change >= 0;

  // Path coordinates for a 600x180 viewbox
  const points = [
    { x: 20, y: 130, price: basePrice * 0.975, volume: 45 },
    { x: 70, y: 115, price: basePrice * 0.982, volume: 60 },
    { x: 120, y: 140, price: basePrice * 0.968, volume: 85 },
    { x: 170, y: 125, price: basePrice * 0.978, volume: 55 },
    { x: 220, y: 95, price: basePrice * 0.992, volume: 70 },
    { x: 270, y: 105, price: basePrice * 0.988, volume: 65 },
    { x: 320, y: 65, price: basePrice * 1.012, volume: 110 },
    { x: 370, y: 80, price: basePrice * 1.004, volume: 80 },
    { x: 420, y: 55, price: basePrice * 1.018, volume: 95 },
    { x: 470, y: 70, price: basePrice * 1.009, volume: 75 },
    { x: 520, y: 40, price: basePrice * 1.025, volume: 125 },
    { x: 570, y: 45, price: basePrice, volume: 100 },
  ];

  // SVG path curve
  const pathD = `M ${points.map((p) => `${p.x},${p.y}`).join(' L ')}`;
  const areaD = `M 20,170 L ${points.map((p) => `${p.x},${p.y}`).join(' L ')} L 570,170 Z`;

  return (
    <div className="terminal-card p-4 relative overflow-hidden flex flex-col gap-2">
      <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
        <div className="flex items-center gap-4">
          <span>OHLC: <strong className="text-slate-200">O {data.ohlc.open} / H {data.ohlc.high} / L {data.ohlc.low} / C {data.ohlc.close}</strong></span>
          <span className="hidden sm:inline">VOL: <strong className="text-slate-200">{(data.volume / 1000000).toFixed(2)}M</strong></span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
          <span className="text-cyan-300">EMA(20)</span>
          <span className="w-2 h-2 rounded-full bg-indigo-400 ml-2"></span>
          <span className="text-indigo-300">SMA(50)</span>
        </div>
      </div>

      {/* SVG Chart Container */}
      <div className="relative w-full h-44 bg-[#090D15] rounded border border-[#162030] p-1">
        <svg
          viewBox="0 0 600 180"
          className="w-full h-full overflow-visible"
          preserveAspectRatio="none"
        >
          <defs>
            <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#06B6D4" stopOpacity="0.3" />
              <stop offset="100%" stopColor="#06B6D4" stopOpacity="0.0" />
            </linearGradient>
            <linearGradient id="gridGrad" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#162234" stopOpacity="0.2" />
              <stop offset="50%" stopColor="#162234" stopOpacity="0.6" />
              <stop offset="100%" stopColor="#162234" stopOpacity="0.2" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          <line x1="0" y1="40" x2="600" y2="40" stroke="#141E2D" strokeDasharray="3 3" />
          <line x1="0" y1="85" x2="600" y2="85" stroke="#141E2D" strokeDasharray="3 3" />
          <line x1="0" y1="130" x2="600" y2="130" stroke="#141E2D" strokeDasharray="3 3" />

          {/* Volume histogram bars at the bottom */}
          {points.map((p, idx) => {
            const barHeight = (p.volume / 130) * 45;
            return (
              <rect
                key={idx}
                x={p.x - 6}
                y={170 - barHeight}
                width="12"
                height={barHeight}
                fill={idx % 2 === 0 ? '#10B981' : '#EF4444'}
                opacity="0.3"
                rx="1"
              />
            );
          })}

          {/* Area under curve */}
          <path d={areaD} fill="url(#chartGradient)" />

          {/* Smooth price line */}
          <path
            d={pathD}
            fill="none"
            stroke="#06B6D4"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Current Price Marker Tag */}
          <g transform={`translate(${points[points.length - 1].x}, ${points[points.length - 1].y})`}>
            <circle r="4" fill="#06B6D4" className="animate-ping" opacity="0.75" />
            <circle r="4" fill="#38BDF8" stroke="#090D15" strokeWidth="2" />
            <line x1="-550" y1="0" x2="0" y2="0" stroke="#38BDF8" strokeDasharray="2 2" opacity="0.4" />
            <rect x="5" y="-10" width="60" height="20" rx="3" fill="#0E2238" stroke="#38BDF8" strokeWidth="1" />
            <text x="12" y="4" fill="#38BDF8" fontSize="10" fontFamily="monospace" fontWeight="bold">
              {data.price.toFixed(1)}
            </text>
          </g>
        </svg>
      </div>
    </div>
  );
};
