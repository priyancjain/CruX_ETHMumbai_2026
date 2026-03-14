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
}

export default function ScoreCard({
  score,
  tier,
  collateral_requirement,
  max_loan_usdc,
  rationale,
  key_factors,
  risk_flags,
}: ScoreCardProps) {
  const [displayScore, setDisplayScore] = useState(0);

  useEffect(() => {
    const duration = 1500;
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

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="glass-card p-8 space-y-6"
    >
      {/* Score + Tier */}
      <div className="flex items-center gap-8">
        <div className="text-center">
          <p className="text-7xl font-display font-extrabold text-white score-glow">
            {displayScore}
          </p>
          <p className="text-xs text-slate-500 font-mono mt-1 tracking-widest">/ 1000</p>
        </div>
        <div className="h-16 w-px bg-surface-3/50" />
        <span className={`tier-badge text-xl tier-${tier}`}>TIER {tier}</span>
      </div>

      {/* Collateral + Max Loan */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-surface-2/60 border border-surface-3/40 rounded-xl p-4">
          <p className="text-[10px] text-slate-500 font-mono tracking-wider uppercase mb-1">COLLATERAL</p>
          <p className="text-2xl font-display font-extrabold text-white">
            {collateral_requirement}<span className="text-sm text-slate-400 font-body font-normal ml-0.5">%</span>
          </p>
        </div>
        <div className="bg-surface-2/60 border border-surface-3/40 rounded-xl p-4">
          <p className="text-[10px] text-slate-500 font-mono tracking-wider uppercase mb-1">MAX LOAN</p>
          <p className="text-2xl font-display font-extrabold text-white">
            ${max_loan_usdc.toLocaleString()}<span className="text-sm text-slate-400 font-body font-normal ml-1">USDC</span>
          </p>
        </div>
      </div>

      {/* Rationale */}
      <div>
        <h3 className="text-[10px] text-slate-500 font-mono tracking-wider uppercase mb-2">RATIONALE</h3>
        <p className="text-sm text-slate-300 leading-relaxed">{rationale}</p>
      </div>

      {/* Key Factors */}
      {key_factors.length > 0 && (
        <div>
          <h3 className="text-[10px] text-slate-500 font-mono tracking-wider uppercase mb-2">KEY FACTORS</h3>
          <div className="flex flex-wrap gap-2">
            {key_factors.map((f, i) => (
              <span key={i} className="px-3 py-1.5 bg-accent/8 text-accent/90 border border-accent/15 rounded-lg text-xs font-medium">
                {f}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Risk Flags */}
      {risk_flags.length > 0 && (
        <div>
          <h3 className="text-[10px] text-red-400/70 font-mono tracking-wider uppercase mb-2">RISK FLAGS</h3>
          <div className="flex flex-wrap gap-2">
            {risk_flags.map((f, i) => (
              <span key={i} className="px-3 py-1.5 bg-red-500/8 text-red-400/90 border border-red-500/15 rounded-lg text-xs font-medium">
                {f}
              </span>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}
