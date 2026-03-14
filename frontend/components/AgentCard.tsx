"use client";

import { useRouter } from "next/navigation";
import PlatformBadge from "./PlatformBadge";

interface AgentCardProps {
  wallet_address: string;
  agent_name: string;
  description?: string;
  platform: string;
  score?: number | null;
  tier?: string | null;
  mcap_usd?: number;
  holder_count?: number;
  image_url?: string;
  is_evm_wallet?: boolean;
  chain?: string;
}

export default function AgentCard({
  wallet_address,
  agent_name,
  description,
  platform,
  score,
  tier,
  mcap_usd,
  holder_count,
  image_url,
  is_evm_wallet,
}: AgentCardProps) {
  const router = useRouter();
  const isEvm = is_evm_wallet !== false && wallet_address?.startsWith("0x");
  const hasScore = score !== null && score !== undefined && tier;

  function handleClick() {
    if (isEvm) {
      router.push(`/agent/${wallet_address}`);
    }
  }

  return (
    <div
      onClick={handleClick}
      className={`glass-card p-5 flex flex-col gap-3
        ${isEvm ? "cursor-pointer hover:border-accent/25 hover:shadow-glow" : "opacity-50 cursor-not-allowed"}
        transition-all duration-300`}
    >
      {/* Top row: avatar + name + badge */}
      <div className="flex items-start gap-3">
        {image_url ? (
          <img
            src={image_url}
            alt={agent_name}
            className="w-10 h-10 rounded-xl object-cover flex-shrink-0 border border-surface-3"
          />
        ) : (
          <div className="w-10 h-10 rounded-xl bg-surface-2 border border-surface-3 flex items-center justify-center flex-shrink-0">
            <span className="text-accent/60 font-display font-bold text-sm">
              {(agent_name || "?")[0]?.toUpperCase()}
            </span>
          </div>
        )}
        <div className="flex-1 min-w-0">
          <h3 className="font-display font-semibold text-white text-sm truncate leading-tight">
            {agent_name || `Agent ${wallet_address?.slice(0, 8)}...`}
          </h3>
          <p className="text-[11px] text-slate-500 font-mono truncate mt-0.5">
            {wallet_address?.slice(0, 10)}...{wallet_address?.slice(-4)}
          </p>
        </div>
        <PlatformBadge platform={platform} />
      </div>

      {/* Description */}
      {description && (
        <p className="text-xs text-slate-400/80 line-clamp-2 leading-relaxed">
          {description}
        </p>
      )}

      {/* Metrics row */}
      {(mcap_usd !== undefined && mcap_usd > 0) ||
      (holder_count !== undefined && holder_count > 0) ? (
        <div className="flex gap-4">
          {mcap_usd !== undefined && mcap_usd > 0 && (
            <div className="text-[11px]">
              <span className="text-slate-500">MCap </span>
              <span className="text-slate-300 font-mono font-medium">
                ${Number(mcap_usd) >= 1e6
                  ? `${(Number(mcap_usd) / 1e6).toFixed(1)}M`
                  : Number(mcap_usd) >= 1e3
                  ? `${(Number(mcap_usd) / 1e3).toFixed(0)}K`
                  : Number(mcap_usd).toFixed(0)}
              </span>
            </div>
          )}
          {holder_count !== undefined && holder_count > 0 && (
            <div className="text-[11px]">
              <span className="text-slate-500">Holders </span>
              <span className="text-slate-300 font-mono font-medium">
                {Number(holder_count) >= 1e3
                  ? `${(Number(holder_count) / 1e3).toFixed(1)}K`
                  : Number(holder_count).toLocaleString()}
              </span>
            </div>
          )}
        </div>
      ) : null}

      {/* Footer divider + score/status */}
      <div className="flex items-center justify-between mt-auto pt-3 border-t border-surface-3/50">
        {hasScore ? (
          <div className="flex items-center gap-2">
            <span className="text-lg font-display font-extrabold text-white">
              {score}
            </span>
            <span className={`tier-badge tier-${tier}`}>{tier}</span>
          </div>
        ) : (
          <span className="text-[11px] text-slate-500 font-mono">
            NOT SCORED
          </span>
        )}
        {isEvm ? (
          <span className="text-[11px] text-accent/50 font-medium tracking-wide">
            ANALYZE &rarr;
          </span>
        ) : (
          <span className="text-[11px] text-slate-600 font-mono">NON-EVM</span>
        )}
      </div>
    </div>
  );
}
