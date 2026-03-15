"use client";

import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart
} from "recharts";
import { getTrends } from "@/lib/api";

interface TransactionTrendProps {
  wallet: string;
}

export default function TransactionTrend({ wallet }: TransactionTrendProps) {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTrends();
  }, [wallet]);

  async function loadTrends() {
    try {
      const result = await getTrends(wallet);
      setData(result.trend || []);
    } catch {
      setData([]);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="glass-card p-6 h-[300px] animate-pulse flex items-center justify-center">
        <p className="text-gray-400 font-mono text-xs">Charting transaction velocity...</p>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="glass-card p-6 h-[300px] flex items-center justify-center border-dashed">
         <p className="text-gray-400 font-mono text-xs italic">Insufficient history for trend analysis.</p>
      </div>
    );
  }

  return (
    <div className="glass-card overflow-hidden h-[300px] flex flex-col">
       <div className="px-6 py-4 border-b border-gray-100 bg-gray-50/50 flex items-center justify-between">
          <h4 className="text-[10px] text-gray-400 font-mono tracking-widest uppercase font-bold">Transaction Momentum</h4>
          <span className="text-[9px] text-[#1DB954] font-mono font-bold bg-[#1DB954]/10 px-1.5 py-0.5 rounded">30D TREND</span>
       </div>
       
       <div className="flex-1 p-4">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#1DB954" stopOpacity={0.1}/>
                <stop offset="95%" stopColor="#1DB954" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
            <XAxis 
              dataKey="date" 
              hide={true} 
            />
            <YAxis 
               tick={{ fill: "#94a3b8", fontSize: 9, fontFamily: "DM Mono" }}
               axisLine={false}
               tickLine={false}
               allowDecimals={false}
            />
            <Tooltip 
              contentStyle={{ backgroundColor: "#0f172a", border: "none", borderRadius: "8px", fontSize: "10px", color: "#fff", fontFamily: "DM Mono" }}
              itemStyle={{ color: "#1DB954" }}
              labelStyle={{ color: "#64748b", marginBottom: "4px" }}
              cursor={{ stroke: '#1DB954', strokeWidth: 1 }}
            />
            <Area 
              type="monotone" 
              dataKey="count" 
              stroke="#1DB954" 
              fillOpacity={1} 
              fill="url(#colorCount)" 
              strokeWidth={2}
              activeDot={{ r: 4, strokeWidth: 0, fill: "#1DB954" }}
              name="Transactions"
            />
          </AreaChart>
        </ResponsiveContainer>
       </div>
    </div>
  );
}
