"use client";

import { motion } from "framer-motion";

interface AIAnalysisProps {
  analysis: {
    summary?: string;
    patterns?: string[];
    risk_indicators?: string[];
    notable_transactions?: any[];
    activity_profile?: string;
  } | null;
}

export default function AIAnalysis({ analysis }: AIAnalysisProps) {
  if (!analysis) {
    return (
      <div className="glass-card p-12 text-center bg-white/50 border-dashed border-2">
        <p className="text-4xl mb-4">🤖</p>
        <h3 className="text-lg font-display font-black text-gray-900">LLM Analysis Pending</h3>
        <p className="text-sm text-gray-500 font-mono mt-2 max-w-md mx-auto">
          Deep behavioral analysis is being generated. This usually takes 30-60 seconds after the initial score request.
        </p>
      </div>
    );
  }

  const { summary, patterns, risk_indicators, notable_transactions, activity_profile } = analysis;

  return (
    <div className="space-y-6">
      {/* Summary Header */}
      <div className="glass-card p-8 bg-gradient-to-br from-white to-gray-50/50">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-[10px] text-gray-400 font-mono tracking-widest uppercase font-bold">
            Trading Personality & Strategy Report
          </h3>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-gray-400 font-mono">PROFILE:</span>
            <span className="text-[10px] font-mono font-bold bg-gray-900 text-white px-2 py-1 rounded">
              {activity_profile?.replace(/_/g, " ").toUpperCase() || "UNKNOWN"}
            </span>
          </div>
        </div>
        
        <p className="text-lg font-display font-medium text-gray-900 leading-relaxed italic border-l-4 border-[#1DB954] pl-6 py-2">
          "{summary || "No behavioral summary available."}"
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Behavioral Patterns */}
        <div className="glass-card p-6 bg-white">
          <h4 className="text-xs font-display font-black text-gray-900 uppercase tracking-tight mb-4 flex items-center gap-2">
             <span className="w-2 h-2 rounded-full bg-blue-500" />
             Observed Patterns
          </h4>
          <div className="space-y-3">
            {patterns?.map((p, i) => (
              <div key={i} className="flex items-start gap-3 p-3 bg-gray-50 rounded-xl border border-gray-100">
                <span className="text-xs text-blue-500 mt-0.5">◈</span>
                <p className="text-sm text-gray-700 font-medium">{p}</p>
              </div>
            )) || <p className="text-xs text-gray-400 font-mono">No patterns detected.</p>}
          </div>
        </div>

        {/* Risk Assessment */}
        <div className="glass-card p-6 bg-white">
          <h4 className="text-xs font-display font-black text-gray-900 uppercase tracking-tight mb-4 flex items-center gap-2">
             <span className="w-2 h-2 rounded-full bg-red-500" />
             AI Risk Assessment
          </h4>
          <div className="space-y-3">
            {risk_indicators && risk_indicators.length > 0 ? (
              risk_indicators.map((r, i) => (
                <div key={i} className="flex items-start gap-3 p-3 bg-red-50 rounded-xl border border-red-100">
                  <span className="text-xs text-red-500 mt-0.5">⚠</span>
                  <p className="text-sm text-red-800 font-bold">{r}</p>
                </div>
              ))
            ) : (
              <div className="flex items-center gap-3 p-4 bg-green-50 rounded-xl border border-green-100">
                <span className="text-lg">✅</span>
                <div>
                  <p className="text-sm text-green-800 font-bold">No High-Risk Patterns</p>
                  <p className="text-[10px] text-green-600 font-mono">Clean behavioral profile detected by LLM.</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Notable Transactions */}
      {notable_transactions && notable_transactions.length > 0 && (
        <div className="glass-card p-6 bg-white">
           <h4 className="text-xs font-display font-black text-gray-900 uppercase tracking-tight mb-4">
             Notable Operations
           </h4>
           <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {notable_transactions.map((tx, i) => (
                <div key={i} className="p-4 border border-gray-100 rounded-xl hover:border-gray-300 transition-colors">
                   <p className="text-[9px] text-gray-400 font-mono font-bold uppercase mb-2">Event {i + 1}</p>
                   <p className="text-sm font-display font-bold text-gray-900 leading-snug">
                     {typeof tx === 'string' ? tx : JSON.stringify(tx)}
                   </p>
                </div>
              ))}
           </div>
        </div>
      )}
      
      <div className="p-4 bg-gray-900 rounded-2xl">
         <div className="flex items-center gap-3">
            <div className="flex -space-x-2">
               {[1,2,3].map(i => (
                 <div key={i} className="w-6 h-6 rounded-full border-2 border-gray-900 bg-gray-800 flex items-center justify-center text-[8px] text-gray-500">
                   {i}
                 </div>
               ))}
            </div>
            <p className="text-[10px] text-gray-400 font-mono">
              THIS REPORT IS GENERATED BY <span className="text-white font-bold">GPS-O3 MODEL</span> BASED ON THE LAST 50 TRANSACTIONS. 
              DECISIONS SHOULD BE VALDIATED ON-CHAIN.
            </p>
         </div>
      </div>
    </div>
  );
}
