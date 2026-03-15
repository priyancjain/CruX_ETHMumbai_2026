"use client";

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";

interface PortfolioAllocationProps {
  shares: { name: string; value: number }[];
}

const COLORS = ["#1DB954", "#5E5CE6", "#007AFF", "#FF9F0A", "#FF3B30", "#94a3b8"];

export default function PortfolioAllocation({ shares }: PortfolioAllocationProps) {
  if (!shares || shares.length === 0) {
    return (
      <div className="glass-card p-6 h-[300px] flex items-center justify-center border-dashed">
         <p className="text-gray-400 font-mono text-xs italic">Portfolio distribution unavailable.</p>
      </div>
    );
  }

  return (
    <div className="glass-card overflow-hidden h-[300px] flex flex-col">
       <div className="px-6 py-4 border-b border-gray-100 bg-gray-50/50 flex items-center justify-between">
          <h4 className="text-[10px] text-gray-400 font-mono tracking-widest uppercase font-bold">Token Allocation</h4>
          <span className="text-[10px] text-gray-400 font-mono font-bold">USD VALUE</span>
       </div>
       
       <div className="flex-1 p-4 flex items-center">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={shares}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={80}
              paddingAngle={5}
              dataKey="value"
              stroke="none"
              animationBegin={0}
              animationDuration={1500}
            >
              {shares.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip 
               contentStyle={{ backgroundColor: "#0f172a", border: "none", borderRadius: "8px", fontSize: "10px", color: "#fff", fontFamily: "DM Mono" }}
               formatter={(value: number) => [`$${value.toLocaleString()}`, "Value"]}
            />
            <Legend 
              verticalAlign="middle" 
              align="right" 
              layout="vertical"
              iconType="circle"
              wrapperStyle={{ fontSize: "10px", fontFamily: "Sora", fontWeight: "bold", paddingLeft: "15px" }}
            />
          </PieChart>
        </ResponsiveContainer>
       </div>
    </div>
  );
}
