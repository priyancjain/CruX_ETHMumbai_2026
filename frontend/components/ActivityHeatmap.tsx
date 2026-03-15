"use client";

import { useMemo } from "react";
import { motion } from "framer-motion";

interface ActivityHeatmapProps {
  data: { date: string; count: number }[];
}

export default function ActivityHeatmap({ data }: ActivityHeatmapProps) {
  // Generate last 90 days grid
  const grid = useMemo(() => {
    const today = new Date();
    const days = [];
    const statsMap = new Map(data.map(d => [d.date, d.count]));

    for (let i = 89; i >= 0; i--) {
      const d = new Date(today);
      d.setDate(d.getDate() - i);
      const dateStr = d.toISOString().split("T")[0];
      const count = statsMap.get(dateStr) || 0;
      days.push({ date: dateStr, count });
    }
    return days;
  }, [data]);

  const getColor = (count: number) => {
    if (count === 0) return "bg-gray-100";
    if (count < 3) return "bg-green-200";
    if (count < 10) return "bg-green-400";
    if (count < 25) return "bg-green-600";
    return "bg-green-800";
  };

  return (
    <div className="glass-card p-6 flex flex-col">
      <div className="mb-6 flex justify-between items-end">
        <div>
          <h3 className="text-[10px] text-gray-400 font-mono tracking-widest uppercase font-bold">
            Activity Heartbeat
          </h3>
          <p className="text-xl font-display font-black text-gray-900 mt-1">Liveness Heatmap</p>
        </div>
        <div className="flex items-center gap-1.5 text-[9px] font-mono text-gray-400">
           <span>Less</span>
           <div className="w-2.5 h-2.5 bg-gray-100 rounded-sm" />
           <div className="w-2.5 h-2.5 bg-green-200 rounded-sm" />
           <div className="w-2.5 h-2.5 bg-green-600 rounded-sm" />
           <div className="w-2.5 h-2.5 bg-green-800 rounded-sm" />
           <span>More</span>
        </div>
      </div>

      <div className="flex flex-wrap gap-1">
        {grid.map((day, i) => (
          <div key={day.date} className="relative group">
            <motion.div
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: i * 0.005 }}
              className={`w-3.5 h-3.5 rounded-sm ${getColor(day.count)} transition-all hover:ring-2 hover:ring-offset-1 hover:ring-gray-300`}
            />
            {/* Tooltip */}
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-50">
               <div className="bg-gray-900 text-white text-[9px] font-mono px-2 py-1 rounded shadow-xl whitespace-nowrap">
                  {day.date}: {day.count} txs
               </div>
               <div className="w-0 h-0 border-l-[4px] border-l-transparent border-r-[4px] border-r-transparent border-t-[4px] border-t-gray-900 mx-auto" />
            </div>
          </div>
        ))}
      </div>
      
      <div className="mt-4 flex justify-between text-[9px] font-mono text-gray-400 uppercase font-bold">
        <span>~3 Months Ago</span>
        <span>Current Velocity</span>
      </div>
    </div>
  );
}
