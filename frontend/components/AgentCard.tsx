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

/** Score → bar fill % (score out of 1000) */
function scorePct(score: number | null | undefined) {
  if (!score) return 0;
  return Math.min(100, Math.round((score / 1000) * 100));
}

/** Score → semantic bar color */
function scoreBarColor(score: number | null | undefined) {
  if (!score) return "bg-gray-200";
  if (score >= 750) return "bg-[#1DB954]";
  if (score >= 500) return "bg-[#007AFF]";
  if (score >= 300) return "bg-[#FF9F0A]";
  return "bg-[#FF3B30]";
}

/** Score → text color */
function scoreTextColor(score: number | null | undefined) {
  if (!score) return "text-gray-400";
  if (score >= 750) return "text-[#1DB954]";
  if (score >= 500) return "text-[#007AFF]";
  if (score >= 300) return "text-[#FF9F0A]";
  return "text-[#FF3B30]";
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
  const hasWallet = !!wallet_address;

  function handleClick() {
    if (hasWallet) router.push(`/agent/${wallet_address}`);
  }

  return (
    <div
      onClick={handleClick}
      className={`glass-card flex flex-col ${hasWallet ? "cursor-pointer" : "opacity-55 cursor-not-allowed"
        } transition-all duration-250 group`}
    >
      {/* Colored top accent based on tier */}
      <div className={`h-1 rounded-t-xl ${tier === "S" ? "bg-[#1DB954]" :
        tier === "A" ? "bg-[#5E5CE6]" :
          tier === "B" ? "bg-[#007AFF]" :
            tier === "C" ? "bg-[#FF9F0A]" :
              tier === "D" ? "bg-[#FF3B30]" :
                "bg-gray-200"
        }`} />

      <div className="p-6 flex flex-col gap-4 flex-1">
        {/* Top: avatar + name + platform */}
        <div className="flex items-start gap-4">
          {image_url ? (
            <img
              src={image_url}
              alt={agent_name}
              className="w-14 h-14 rounded-xl object-cover flex-shrink-0 border border-gray-200 shadow-sm"
            />
          ) : (
            <div className="w-14 h-14 rounded-xl bg-[#1DB954]/10 border border-[#1DB954]/20 flex items-center justify-center flex-shrink-0">
              <span className="text-[#1DB954] font-display font-black text-xl">
                {(agent_name || "?")[0]?.toUpperCase()}
              </span>
            </div>
          )}
          <div className="flex-1 min-w-0">
            <h3 className="font-display font-bold text-gray-900 text-base truncate leading-tight group-hover:text-[#1DB954] transition-colors">
              {agent_name || `Agent ${wallet_address?.slice(0, 8)}...`}
            </h3>
            <p className="text-[11px] text-gray-400 font-mono mt-1 truncate">
              {wallet_address?.slice(0, 12)}...{wallet_address?.slice(-4)}
            </p>
            <div className="mt-2">
              <PlatformBadge platform={platform} />
            </div>
          </div>
        </div>

        {/* Description — more lines, better reading */}
        {description && (
          <p className="text-[13px] text-gray-500 leading-relaxed line-clamp-2">
            {description}
          </p>
        )}

        {/* Metrics row */}
        {((mcap_usd !== undefined && mcap_usd > 0) ||
          (holder_count !== undefined && holder_count > 0)) && (
            <div className="flex gap-5 py-2 border-t border-b border-gray-100">
              {mcap_usd !== undefined && mcap_usd > 0 && (
                <div>
                  <p className="text-[10px] text-gray-400 font-mono tracking-widest uppercase">MCap</p>
                  <p className="text-sm text-gray-800 font-mono font-semibold mt-0.5">
                    ${Number(mcap_usd) >= 1e6
                      ? `${(Number(mcap_usd) / 1e6).toFixed(1)}M`
                      : Number(mcap_usd) >= 1e3
                        ? `${(Number(mcap_usd) / 1e3).toFixed(0)}K`
                        : Number(mcap_usd).toFixed(0)}
                  </p>
                </div>
              )}
              {holder_count !== undefined && holder_count > 0 && (
                <div>
                  <p className="text-[10px] text-gray-400 font-mono tracking-widest uppercase">Holders</p>
                  <p className="text-sm text-gray-800 font-mono font-semibold mt-0.5">
                    {Number(holder_count) >= 1e3
                      ? `${(Number(holder_count) / 1e3).toFixed(1)}K`
                      : Number(holder_count).toLocaleString()}
                  </p>
                </div>
              )}
            </div>
          )}

        {/* Score section — larger, with progress bar */}
        <div className="mt-auto">
          {hasScore ? (
            <div className="space-y-2">
              <div className="flex items-end justify-between">
                <div className="flex items-baseline gap-1.5">
                  <span className={`text-3xl font-display font-black ${scoreTextColor(score)}`}>
                    {score}
                  </span>
                  <span className="text-gray-300 text-sm font-mono">/1000</span>
                </div>
                <span className={`tier-badge tier-${tier}`}>{tier}</span>
              </div>
              {/* Score progress bar */}
              <div className="w-full bg-gray-100 rounded-full h-1.5 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${scoreBarColor(score)}`}
                  style={{ width: `${scorePct(score)}%` }}
                />
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-between">
              <span className="text-[11px] text-gray-400 font-mono bg-gray-100 px-2.5 py-1 rounded-md">
                NOT YET SCORED
              </span>
              {hasWallet && (
                <span className="text-xs text-[#1DB954] font-display font-bold opacity-0 group-hover:opacity-100 transition-opacity">
                  Score Now →
                </span>
              )}
            </div>
          )}
        </div>

        {/* CTA row */}
        {hasWallet && (
          <div className="pt-2 border-t border-gray-100 flex items-center justify-between">
            <span className="text-[11px] text-gray-400 font-mono">
              {isEvm ? "EVM" : "NON-EVM"} · {platform}
            </span>
            <span className="text-[11px] text-[#1DB954] font-display font-bold tracking-wide opacity-0 group-hover:opacity-100 translate-x-[-4px] group-hover:translate-x-0 transition-all">
              Analyze →
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
