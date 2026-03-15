"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";

interface ScoreCardProps {
  score: number;
  tier: string;
  collateral_requirement: number;
  max_loan_usdc: number;
  rationale: string;
  key_factors: string[];
  risk_flags: string[];
  ensip25_verified?: boolean;
  ens_name?: string | null;
}

const TIER_CONFIG: Record<string, { color: string; bg: string; border: string; label: string }> = {
  S: { color: "#1DB954", bg: "#1DB95412", border: "#1DB95430", label: "Excellent" },
  A: { color: "#5E5CE6", bg: "#5E5CE612", border: "#5E5CE630", label: "Very Good" },
  B: { color: "#007AFF", bg: "#007AFF12", border: "#007AFF30", label: "Good" },
  C: { color: "#FF9F0A", bg: "#FF9F0A12", border: "#FF9F0A30", label: "Fair" },
  D: { color: "#FF3B30", bg: "#FF3B3012", border: "#FF3B3030", label: "Poor" },
};

export default function ScoreCard({
  score,
  tier,
  collateral_requirement,
  max_loan_usdc,
  rationale,
  key_factors,
  risk_flags,
  ensip25_verified = false,
  ens_name,
}: ScoreCardProps) {
  const [displayScore, setDisplayScore] = useState(0);
  const tierCfg = TIER_CONFIG[tier] || TIER_CONFIG["D"];

  useEffect(() => {
    const duration = 1200;
    const steps = 60;
    const increment = score / steps;
    let current = 0;
    const timer = setInterval(() => {
      current += increment;
      if (current >= score) {
        setDisplayScore(score);
        clearInterval(timer);
      } else {
        setDisplayScore(Math.floor(current));
      }
    }, duration / steps);
    return () => clearInterval(timer);
  }, [score]);

  const pct = Math.min(100, Math.round((score / 1000) * 100));

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45 }}
      className="glass-card overflow-hidden"
    >
      {/* Tier color accent bar */}
      <div className="h-1.5" style={{ background: tierCfg.color }} />

      <div className="p-8 space-y-6">

        {/* Score + Tier row */}
        <div className="flex items-center gap-10">
          {/* Main Score Display */}
          <div className="flex flex-col">
            <p className="text-[10px] text-gray-400 font-mono tracking-widest uppercase font-bold mb-1">0xTrust Credit Rating</p>
            <div className="flex items-baseline gap-2">
              <span className="text-8xl font-display font-black tracking-tighter" style={{ color: tierCfg.color }}>
                {displayScore}
              </span>
              <span className="text-xl text-gray-400 font-mono font-bold">/ 1000</span>
            </div>
          </div>

          <div className="h-24 w-px bg-gray-100 hidden md:block" />

          {/* Gauge / Runner */}
          <div className="flex-1 space-y-4">
             <div className="flex justify-between items-end">
                <div className="space-y-0.5">
                   <p className="text-[10px] text-gray-400 font-mono font-bold">CURRENT TIER</p>
                   <p className="text-2xl font-display font-black text-gray-900">Tier {tier}</p>
                </div>
                <div className="text-right space-y-0.5">
                   <p className="text-[10px] text-gray-400 font-mono font-bold">OUTCOME</p>
                   <p className="text-sm font-display font-bold text-gray-600 italic">{tierCfg.label}</p>
                </div>
             </div>

             {/* Runner Track */}
             <div className="relative h-4 bg-gray-100 rounded-full overflow-hidden border border-gray-200/50">
                {/* Segments */}
                <div className="absolute inset-0 flex">
                   {[...Array(10)].map((_, i) => (
                      <div key={i} className="flex-1 border-r border-white/40 last:border-0" />
                   ))}
                </div>
                {/* Runner Fill */}
                <motion.div 
                  initial={{ width: 0 }}
                  animate={{ width: `${pct}%` }}
                  transition={{ duration: 1, ease: "easeOut" }}
                  className="absolute inset-y-0 left-0 rounded-full"
                  style={{ 
                    background: `linear-gradient(90deg, ${tierCfg.color}88 0%, ${tierCfg.color} 100%)`,
                    boxShadow: `0 0 20px ${tierCfg.color}44`
                  }}
                />
             </div>
             
             {/* Dynamic Rating Label */}
             <div className="flex justify-between text-[9px] font-mono font-bold text-gray-400 uppercase tracking-tighter">
                <span>Critical</span>
                <span>Sub-Prime</span>
                <span>Standard</span>
                <span>Institutional</span>
                <span>Elite</span>
             </div>
          </div>
        </div>

        {/* Info Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white border border-gray-100 shadow-sm rounded-2xl p-5 flex flex-col justify-between hover:border-gray-200 transition-all">
            <p className="text-[10px] text-gray-400 font-mono tracking-widest uppercase font-bold mb-4">Collateral Requirement</p>
            <div className="flex items-baseline gap-1">
              <span className="text-4xl font-display font-black text-gray-900">{collateral_requirement}</span>
              <span className="text-lg text-gray-400 font-mono font-bold">%</span>
            </div>
            <p className="text-[9px] text-gray-400 font-mono mt-2">Locked asset ratio needed for liquidity access.</p>
          </div>

          <div className="bg-white border border-gray-100 shadow-sm rounded-2xl p-5 flex flex-col justify-between hover:border-gray-200 transition-all">
            <p className="text-[10px] text-gray-400 font-mono tracking-widest uppercase font-bold mb-4">Max Liquidity Access</p>
            <div className="flex items-baseline gap-1">
              <span className="text-4xl font-display font-black text-[#1DB954]">${max_loan_usdc.toLocaleString()}</span>
              <span className="text-lg text-gray-400 font-mono font-bold">USDC</span>
            </div>
            <p className="text-[9px] text-gray-400 font-mono mt-2">Maximum non-custodial borrowing capacity.</p>
          </div>

          <div className="bg-white border border-gray-100 shadow-sm rounded-2xl p-5 flex flex-col justify-between hover:border-gray-200 transition-all">
             <p className="text-[10px] text-gray-400 font-mono tracking-widest uppercase font-bold mb-4">Identity Verification</p>
             <div className={`flex items-center gap-2 text-xl font-display font-black ${ensip25_verified ? 'text-[#1DB954]' : 'text-gray-300'}`}>
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
                </svg>
                {ensip25_verified ? 'ENSIP-25 Verified' : 'Unverified'}
             </div>
             <p className="text-[9px] text-gray-400 font-mono mt-2 truncate">
               {ensip25_verified ? `Linked to ${ens_name}` : 'Self-sovereign identity not detected.'}
             </p>
          </div>
        </div>


        {/* Rationale */}
        <div className="bg-gray-50 border border-gray-100 rounded-xl p-6">
          <div className="flex items-start gap-4">
            <div className="flex-1 space-y-2">
              <h3 className="text-[10px] text-gray-400 font-mono tracking-widest uppercase font-bold">Underwriting Rationale</h3>
              <p className="text-sm text-gray-700 leading-relaxed font-medium">{rationale}</p>
            </div>
            
            {/* Decision Quality Tags */}
            <div className="hidden md:flex flex-col gap-2 w-48 shrink-0">
               <div className="p-2 bg-white border border-gray-100 rounded-lg shadow-sm">
                  <p className="text-[9px] text-gray-400 font-mono font-bold uppercase mb-1">Signal Strength</p>
                  <div className="flex gap-1">
                    {[1,2,3,4,5].map(i => (
                      <div key={i} className={`h-1 flex-1 rounded-full ${i <= Math.ceil(score/200) ? 'bg-[#1DB954]' : 'bg-gray-100'}`} />
                    ))}
                  </div>
               </div>
               <div className="p-2 bg-white border border-gray-100 rounded-lg shadow-sm">
                  <p className="text-[9px] text-gray-400 font-mono font-bold uppercase mb-1">Decision Quality</p>
                  <p className="text-[10px] font-display font-bold text-gray-900">
                    {score > 700 ? "Institutional Grade" : score > 400 ? "Standard Risk" : "High Concentrated Risk"}
                  </p>
               </div>
            </div>
          </div>
        </div>

        {/* Key Factors & Risk Breakdown */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Support Signals */}
          <div className="space-y-3">
            <h3 className="text-[10px] text-[#1DB954] font-mono tracking-widest uppercase font-bold flex items-center gap-2">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><path d="M12 19V5"/><path d="m5 12 7-7 7 7"/></svg>
              Bullish Factors
            </h3>
            <div className="flex flex-wrap gap-2">
              {key_factors.length > 0 ? key_factors.map((f, i) => (
                <span
                  key={i}
                  className="px-3 py-1.5 bg-[#1DB954]/05 text-[#1DB954] border border-[#1DB954]/10 rounded-lg text-[11px] font-bold font-display"
                >
                  {f}
                </span>
              )) : (
                <p className="text-[10px] text-gray-400 font-mono italic">No major bullish signals detected.</p>
              )}
            </div>
          </div>

          {/* Friction points */}
          <div className="space-y-3">
             <h3 className="text-[10px] text-[#FF3B30] font-mono tracking-widest uppercase font-bold flex items-center gap-2">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><path d="M12 5v14"/><path d="m19 12-7 7-7-7"/></svg>
              Risk Indicators
            </h3>
            <div className="flex flex-wrap gap-2">
              {risk_flags.length > 0 ? risk_flags.map((f, i) => (
                <span
                  key={i}
                  className="px-3 py-1.5 bg-[#FF3B30]/05 text-[#FF3B30] border border-[#FF3B30]/10 rounded-lg text-[11px] font-bold font-display"
                >
                  {f}
                </span>
              )) : (
                <p className="text-[10px] text-gray-400 font-mono italic">No critical risk flags detected.</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

