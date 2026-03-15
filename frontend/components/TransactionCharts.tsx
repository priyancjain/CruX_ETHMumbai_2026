"use client";

import { useState, useEffect } from "react";
import { getTransactions } from "@/lib/api";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";

interface TransactionChartsProps {
  wallet: string;
}

const COLORS = ["#1DB954", "#3b82f6", "#8b5cf6", "#f59e0b", "#ef4444", "#06b6d4"];

export default function TransactionCharts({ wallet }: TransactionChartsProps) {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        // Fetching 100 transactions to get a better overview
        const result = await getTransactions(wallet, 1, 100);
        setData(result.transactions || []);
      } catch (error) {
        console.error("Error fetching transactions for charts:", error);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [wallet]);

  // Process data for Pie Chart (Token Types)
  const tokenDistribution = data.reduce((acc: any[], current) => {
    const type = current.tx_type || "Unknown";
    const existing = acc.find((item) => item.name === type);
    if (existing) {
      existing.value += 1;
    } else {
      acc.push({ name: type, value: 1 });
    }
    return acc;
  }, []);

  // Process data for Line Chart (Activity over time)
  const activityData = data
    .filter((tx) => tx.timestamp)
    .reduce((acc: any[], current) => {
      const date = new Date(current.timestamp).toLocaleDateString();
      const existing = acc.find((item) => item.date === date);
      if (existing) {
        existing.count += 1;
      } else {
        acc.push({ date, count: 1 });
      }
      return acc;
    }, [])
    // Sort by date (assuming reverse choronological usually, but we want timeline)
    .reverse();

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-pulse">
        <div className="glass-card h-64 flex items-center justify-center">
          <p className="text-gray-400 font-mono text-xs">Loading Pie Chart...</p>
        </div>
        <div className="glass-card h-64 flex items-center justify-center">
          <p className="text-gray-400 font-mono text-xs">Loading Activity Chart...</p>
        </div>
      </div>
    );
  }

  if (data.length === 0) {
    return null;
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* Pie Chart: Token Type Distribution */}
      <div className="glass-card p-6">
        <h3 className="text-[10px] text-gray-400 font-mono tracking-widest uppercase mb-4">
          Token Type Distribution
        </h3>
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={tokenDistribution}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={80}
                paddingAngle={5}
                dataKey="value"
              >
                {tokenDistribution.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip 
                contentStyle={{ backgroundColor: '#111', border: '1px solid #333', borderRadius: '8px' }}
                itemStyle={{ color: '#fff' }}
              />
              <Legend verticalAlign="bottom" height={36}/>
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Line Chart: Transaction Activity */}
      <div className="glass-card p-6">
        <h3 className="text-[10px] text-gray-400 font-mono tracking-widest uppercase mb-4">
          Transaction Activity (Recent 100)
        </h3>
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={activityData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#222" vertical={false} />
              <XAxis 
                dataKey="date" 
                stroke="#666" 
                fontSize={10} 
                tickLine={false} 
                axisLine={false} 
              />
              <YAxis 
                stroke="#666" 
                fontSize={10} 
                tickLine={false} 
                axisLine={false} 
              />
              <Tooltip 
                contentStyle={{ backgroundColor: '#111', border: '1px solid #333', borderRadius: '8px' }}
                itemStyle={{ color: '#1DB954' }}
              />
              <Line 
                type="monotone" 
                dataKey="count" 
                stroke="#1DB954" 
                strokeWidth={2} 
                dot={{ r: 4, fill: "#1DB954" }} 
                activeDot={{ r: 6 }} 
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
