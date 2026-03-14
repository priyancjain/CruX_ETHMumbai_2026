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
    <div className="glass-card p-6">
      <h3 className="text-[10px] text-slate-500 font-mono tracking-wider uppercase mb-4">
        FINANCIAL PERFORMANCE (90D)
      </h3>

      {/* Main PnL */}
      <div className="flex items-center gap-4 mb-6">
        <div>
          <p className="text-[10px] text-slate-500 font-mono">TOTAL P&L</p>
          <p
            className={`text-3xl font-display font-extrabold ${
              isProfit ? "text-emerald-400" : "text-red-400"
            }`}
          >
            {isProfit ? "+" : ""}
            {formatUSD(pnl.total_pnl_usd)}
          </p>
        </div>

        {/* Win Rate Circle */}
        <div className="ml-auto flex flex-col items-center">
          <div className="relative w-16 h-16">
            <svg className="w-16 h-16 -rotate-90" viewBox="0 0 64 64">
              <circle
                cx="32"
                cy="32"
                r="28"
                fill="none"
                stroke="#1e293b"
                strokeWidth="4"
              />
              <circle
                cx="32"
                cy="32"
                r="28"
                fill="none"
                stroke={winPct >= 50 ? "#34d399" : "#f87171"}
                strokeWidth="4"
                strokeDasharray={`${(winPct / 100) * 175.9} 175.9`}
                strokeLinecap="round"
              />
            </svg>
            <span className="absolute inset-0 flex items-center justify-center text-sm font-mono font-bold text-slate-200">
              {winPct}%
            </span>
          </div>
          <p className="text-[9px] text-slate-500 font-mono mt-1">WIN RATE</p>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatBox label="Realized" value={formatUSD(pnl.realized_pnl_usd)} positive={pnl.realized_pnl_usd >= 0} />
        <StatBox label="Unrealized" value={formatUSD(pnl.unrealized_pnl_usd)} positive={pnl.unrealized_pnl_usd >= 0} />
        <StatBox label="Total Trades" value={String(pnl.total_trades)} />
        <StatBox label="Profitable" value={String(pnl.profitable_trades)} />
        <StatBox label="Avg Trade" value={formatUSD(pnl.avg_trade_size_usd)} />
        <StatBox label="Largest Win" value={formatUSD(pnl.largest_win_usd)} positive />
        <StatBox label="Largest Loss" value={formatUSD(pnl.largest_loss_usd)} positive={false} />
        <StatBox label="Tokens Traded" value={String(pnl.tokens_traded?.length || 0)} />
      </div>

      {pnl.snapshot_at && (
        <p className="text-[9px] text-slate-600 font-mono mt-3 text-right">
          Last updated: {new Date(pnl.snapshot_at).toLocaleDateString()}
        </p>
      )}
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
    <div className="bg-surface-2/40 border border-surface-3/30 rounded-lg p-2.5">
      <p className="text-[9px] text-slate-500 font-mono">{label}</p>
      <p
        className={`text-sm font-mono font-medium mt-0.5 ${
          positive === true
            ? "text-emerald-400"
            : positive === false
            ? "text-red-400"
            : "text-slate-200"
        }`}
      >
        {value}
      </p>
    </div>
  );
}
