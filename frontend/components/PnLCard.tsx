"use client";

interface PnLCardProps {
  pnl: {
    total_pnl_usd: number;
    realized_pnl_usd: number;
    unrealized_pnl_usd: number;
    win_rate: number;
    total_trades: number;
    profitable_trades: number;
    avg_trade_size_usd: number;
    largest_win_usd: number;
    largest_loss_usd: number;
    tokens_traded: string[];
    snapshot_at?: string;
  };
}


function formatUSD(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`;
  if (abs >= 1_000) return `$${(value / 1_000).toFixed(2)}K`;
  return `$${value.toFixed(2)}`;
}

export default function PnLCard({ pnl }: PnLCardProps) {
  const isProfit = pnl.total_pnl_usd >= 0;
  const winPct = Math.round((pnl.win_rate || 0) * 100);

  return (
    <div className="glass-card overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-100 bg-gray-50/50 flex items-center justify-between">
        <h3 className="text-[10px] text-gray-400 font-mono tracking-widest uppercase font-bold">
          FINANCIAL PERFORMANCE (90D)
        </h3>
        {pnl.snapshot_at && (
          <span className="text-[9px] text-gray-400 font-mono">
            SYNCED {new Date(pnl.snapshot_at).toLocaleDateString()}
          </span>
        )}
      </div>

      <div className="p-6 space-y-8">
        {/* Main PnL */}
        <div className="flex items-center gap-10">
          <div className="space-y-1">
            <p className="text-[10px] text-gray-400 font-mono font-bold tracking-tight">TOTAL AGENT P&L</p>
            <p
              className={`text-5xl font-display font-black tracking-tighter ${
                isProfit ? "text-[#1DB954]" : "text-[#FF3B30]"
              }`}
            >
              {isProfit ? "+" : ""}
              {formatUSD(pnl.total_pnl_usd)}
            </p>
          </div>

          <div className="h-16 w-px bg-gray-100" />

          {/* Win Rate Circle */}
          <div className="flex items-center gap-4">
            <div className="relative w-16 h-16">
              <svg className="w-16 h-16 -rotate-90" viewBox="0 0 64 64">
                <circle
                  cx="32"
                  cy="32"
                  r="28"
                  fill="none"
                  stroke="#f1f5f9"
                  strokeWidth="5"
                />
                <circle
                  cx="32"
                  cy="32"
                  r="28"
                  fill="none"
                  stroke={winPct >= 50 ? "#1DB954" : "#FF3B30"}
                  strokeWidth="5"
                  strokeDasharray={`${(winPct / 100) * 175.9} 175.9`}
                  strokeLinecap="round"
                />
              </svg>
              <span className="absolute inset-0 flex items-center justify-center text-sm font-mono font-black text-gray-900">
                {winPct}%
              </span>
            </div>
            <div className="space-y-0.5">
              <p className="text-[10px] text-gray-400 font-mono font-bold">ACCURACY</p>
              <p className="text-xs font-display font-bold text-gray-900">Win Rate</p>
            </div>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatBox label="Realized Gains" value={formatUSD(pnl.realized_pnl_usd)} positive={pnl.realized_pnl_usd >= 0} />
          <StatBox label="Unrealized Value" value={formatUSD(pnl.unrealized_pnl_usd)} positive={pnl.unrealized_pnl_usd >= 0} />
          <StatBox label="Execution Count" value={String(pnl.total_trades)} />
          <StatBox label="Successes" value={String(pnl.profitable_trades)} />
          <StatBox label="Avg Entry Size" value={formatUSD(pnl.avg_trade_size_usd)} />
          <StatBox label="Max Peak" value={formatUSD(pnl.largest_win_usd)} positive />
          <StatBox label="Max Drawdown" value={formatUSD(pnl.largest_loss_usd)} positive={false} />
          <StatBox label="Asset Breadth" value={String(pnl.tokens_traded?.length || 0)} />
        </div>
      </div>
    </div>
  );
}

function StatBox({
  label,
  value,
  positive,
}: {
  label: string;
  value: string;
  positive?: boolean;
}) {
  return (
    <div className="bg-gray-50 border border-gray-100 rounded-xl p-3 hover:border-gray-200 transition-colors">
      <p className="text-[9px] text-gray-400 font-mono font-bold uppercase mb-1">{label}</p>
      <p
        className={`text-sm font-mono font-bold ${
          positive === true
            ? "text-[#1DB954]"
            : positive === false
            ? "text-[#FF3B30]"
            : "text-gray-900"
        }`}
      >
        {value}
      </p>
    </div>
  );
}

