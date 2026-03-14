"use client";

import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid, ReferenceLine } from "recharts";

interface PnLEquityCurveProps {
  data: { date: string; value: number }[];
}

export default function PnLEquityCurve({ data }: PnLEquityCurveProps) {
  const isEmpty = !data || data.length === 0;
  
  // Find min/max for Y axis scaling
  const values = data.map(d => d.value);
  const minVal = values.length ? Math.min(...values) : 0;
  const maxVal = values.length ? Math.max(...values) : 0;
  const diff = maxVal - minVal;
  const padding = diff * 0.2 || 100;

  return (
    <div className="glass-card p-6 h-[400px] flex flex-col">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-[10px] text-gray-400 font-mono tracking-widest uppercase font-bold">
            Cumulative PnL (Alpha)
          </h3>
          <p className="text-xl font-display font-black text-gray-900 mt-1">Equity Curve</p>
        </div>
        {!isEmpty && data.length > 0 && (
           <div className={`px-2 py-1 rounded text-[10px] font-mono font-bold ${data[data.length-1].value >= 0 ? 'bg-green-50 text-green-600 border border-green-100' : 'bg-red-50 text-red-600 border border-red-100'}`}>
             {data[data.length-1].value >= 0 ? '+' : ''}{data[data.length-1].value.toLocaleString('en-US', { style: 'currency', currency: 'USD' })}
           </div>
        )}
      </div>

      <div className="flex-1 w-full">
        {isEmpty ? (
          <div className="h-full w-full flex flex-col items-center justify-center border-2 border-dashed border-gray-100 rounded-xl">
            <p className="text-gray-400 font-mono text-xs italic">No historical PnL data available.</p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="pnlCurveGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#1DB954" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#1DB954" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="lossCurveGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#FF3B30" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#FF3B30" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
              <XAxis 
                dataKey="date" 
                axisLine={false} 
                tickLine={false} 
                tick={{ fontSize: 9, fill: '#9ca3af', fontFamily: 'var(--font-mono)' }}
                minTickGap={30}
              />
              <YAxis 
                axisLine={false} 
                tickLine={false} 
                tick={{ fontSize: 9, fill: '#9ca3af', fontFamily: 'var(--font-mono)' }}
                domain={[minVal - padding, maxVal + padding]}
                tickFormatter={(val) => `$${Math.abs(val) >= 1000 ? (val/1000).toFixed(1)+'k' : val}`}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const val = payload[0].value as number;
                    return (
                      <div className="bg-gray-900 border border-gray-800 p-2 rounded-lg shadow-xl font-mono text-[10px]">
                        <p className="text-gray-400 mb-1">{payload[0].payload.date}</p>
                        <p className={val >= 0 ? 'text-[#1DB954] font-bold' : 'text-[#FF3B30] font-bold'}>
                          {val >= 0 ? '+' : ''}{val.toLocaleString('en-US', { style: 'currency', currency: 'USD' })}
                        </p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <ReferenceLine y={0} stroke="#e5e7eb" strokeWidth={1} />
              <Area
                type="monotone"
                dataKey="value"
                stroke={data[data.length-1].value >= 0 ? "#1DB954" : "#FF3B30"}
                strokeWidth={2}
                fillOpacity={1}
                fill={data[data.length-1].value >= 0 ? "url(#pnlCurveGradient)" : "url(#lossCurveGradient)"}
                animationDuration={1500}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
