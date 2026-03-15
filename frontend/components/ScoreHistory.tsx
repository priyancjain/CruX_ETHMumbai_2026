"use client";

interface ScoreEntry {
  score: number;
  tier: string;
  scored_at: string;
  model_used: string;
}


const TIER_COLORS: Record<string, string> = {
  S: "#1DB954",
  A: "#5E5CE6",
  B: "#007AFF",
  C: "#FF9F0A",
  D: "#FF3B30",
};

export default function ScoreHistory({ scores }: { scores: ScoreEntry[] }) {
  if (!scores || scores.length === 0) {
    return (
      <div className="glass-card p-6 h-full flex flex-col items-center justify-center border-dashed">
         <p className="text-gray-400 font-mono text-xs italic">Historical credit logs empty.</p>
      </div>
    );
  }

  return (
    <div className="glass-card overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-100 bg-gray-50/50 flex items-center justify-between">
        <h3 className="text-[10px] text-gray-400 font-mono tracking-widest uppercase font-bold">
          UNDERWRITING HISTORY
        </h3>
        <span className="text-[9px] text-gray-400 font-mono">LATEST {scores.length} AUDITS</span>
      </div>

      <div className="p-4 space-y-2 max-h-[232px] overflow-y-auto custom-scrollbar">
        {scores.map((s, i) => (
          <div
            key={i}
            className="flex items-center justify-between bg-white border border-gray-100 hover:border-gray-200 rounded-xl px-4 py-3 transition-colors shadow-sm"
          >
            <div className="flex items-center gap-4">
              <span className="text-xl font-display font-black text-gray-900 leading-none">
                {s.score}
              </span>
              <div 
                className="w-1.5 h-6 rounded-full" 
                style={{ backgroundColor: TIER_COLORS[s.tier] || "#94a3b8" }} 
              />
              <div className="space-y-0.5">
                 <p className="text-[10px] text-gray-400 font-mono font-bold leading-tight uppercase">Audit Outcome</p>
                 <p className="text-xs font-display font-bold text-gray-700">Tier {s.tier}</p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-[9px] text-gray-400 font-mono font-bold uppercase mb-0.5">Timestamp</p>
              <p className="text-[10px] text-gray-500 font-mono bg-gray-50 px-2 py-0.5 rounded border border-gray-100">
                {new Date(s.scored_at).toLocaleDateString()}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
