"use client";

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";

interface WinLossRatioProps {
  wins: number;
  losses: number;
}

export default function WinLossRatio({ wins, losses }: WinLossRatioProps) {
  const data = [
    { name: "Profitable Exits", value: wins, color: "#1DB954" },
    { name: "Loss-making Exits", value: losses, color: "#FF3B30" },
  ];

  const total = wins + losses;
  const winRate = total > 0 ? ((wins / total) * 100).toFixed(1) : "0";

  return (
    <div className="glass-card p-6 h-[300px] flex flex-col">
      <div className="mb-4">
        <h3 className="text-[10px] text-gray-400 font-mono tracking-widest uppercase font-bold">
          Win/Loss Ratio
        </h3>
        <p className="text-xl font-display font-black text-gray-900 mt-1">{winRate}% Success</p>
      </div>

      <div className="flex-1 relative">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              innerRadius={60}
              outerRadius={80}
              paddingAngle={5}
              dataKey="value"
              animationDuration={1000}
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip 
               contentStyle={{ backgroundColor: '#111827', border: 'none', borderRadius: '8px', color: '#fff', fontSize: '10px', fontFamily: 'var(--font-mono)' }}
               itemStyle={{ color: '#fff' }}
            />
            <Legend 
              verticalAlign="bottom" 
              align="center"
              iconType="circle"
              formatter={(value) => <span className="text-[10px] font-mono text-gray-500">{value}</span>}
            />
          </PieChart>
        </ResponsiveContainer>
        
        {/* Center Label */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none pb-6">
          <div className="text-center">
            <p className="text-[10px] font-mono text-gray-400 leading-tight">TOTAL</p>
            <p className="text-lg font-display font-black text-gray-900">{total}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
