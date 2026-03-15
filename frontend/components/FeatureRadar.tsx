"use client";

import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
} from "recharts";

interface FeatureRadarProps {
  features: Record<string, any>;
}

function normalize(value: number, max: number): number {
  return Math.min(100, Math.round((value / max) * 100));
}

export default function FeatureRadar({ features }: FeatureRadarProps) {

  const data = [
    { label: "Wallet Age", value: normalize(features.wallet_age_days || 0, 1000) },
    { label: "90D Act", value: normalize(features.tx_count_90d || 0, 500) },
    { label: "NAV (USD)", value: normalize(features.tvl_usd || 0, 100000) },
    { label: "Protocols", value: normalize(features.defi_protocol_count || 0, 20) },
    { label: "Reputation", value: normalize(features.erc8004_reputation || 0, 10) },
    { label: "Jobs", value: normalize(features.erc8004_job_count || 0, 100) },
    { label: "Platforms", value: normalize(features.platform_count || 0, 5) },
    { label: "Chains", value: normalize(features.cross_chain_count || 0, 5) },
    { label: "Liquidity", value: normalize((features.balance_eth || 0) + (features.balance_usdc || 0) / 3000, 10) },
    { label: "Profitability", value: normalize(Math.max(features.total_pnl_usd || 0, 0), 50000) },
    { label: "Win Rate", value: normalize((features.win_rate || 0) * 100, 100) },
    { label: "Safety", value: normalize(100 - (features.heyelsa_risk_score || 0), 100) },
  ];


  return (
    <div className="glass-card p-6">
      <h3 className="text-[10px] text-slate-500 font-mono tracking-wider uppercase mb-4">
        FEATURE ANALYSIS (12 AXES)
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <RadarChart data={data}>
          <PolarGrid stroke="#1a2236" strokeDasharray="3 3" />
          <PolarAngleAxis
            dataKey="label"
            tick={{ fill: "#64748b", fontSize: 10, fontFamily: "IBM Plex Mono" }}
          />
          <PolarRadiusAxis
            angle={30}
            domain={[0, 100]}
            tick={{ fill: "#334155", fontSize: 9 }}
            axisLine={false}
          />
          <Radar
            name="Features"
            dataKey="value"
            stroke="#06d6a0"
            fill="#06d6a0"
            fillOpacity={0.12}
            strokeWidth={2}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
