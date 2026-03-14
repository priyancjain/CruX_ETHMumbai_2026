"use client";

interface ScoreEntry {
  score: number;
  tier: string;
  scored_at: string;
  model_used: string;
}

export default function ScoreHistory({ scores }: { scores: ScoreEntry[] }) {
  if (!scores || scores.length === 0) return null;

  return (
    <div className="glass-card p-6">
      <h3 className="text-[10px] text-slate-500 font-mono tracking-wider uppercase mb-4">
        SCORE HISTORY
      </h3>
      <div className="space-y-2">
        {scores.map((s, i) => (
          <div
            key={i}
            className="flex items-center justify-between bg-surface-2/40 border border-surface-3/30 rounded-xl px-4 py-3"
          >
            <div className="flex items-center gap-3">
              <span className="text-lg font-display font-extrabold text-white">
                {s.score}
              </span>
              <span className={`tier-badge text-xs tier-${s.tier}`}>
                {s.tier}
              </span>
            </div>
            <div className="text-[11px] text-slate-500 font-mono">
              {new Date(s.scored_at).toLocaleDateString()} &middot; {s.model_used}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
