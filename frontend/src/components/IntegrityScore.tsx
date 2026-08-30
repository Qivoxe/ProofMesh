interface IntegrityScoreProps {
  fusion: {
    evidence_integrity_score: number;
    risk_level: string;
    confidence: number;
    explanation: string;
  } | undefined;
}

const RISK_COLORS: Record<string, string> = {
  LOW: "text-emerald-300 border-emerald-500/30 bg-emerald-500/10",
  MODERATE: "text-amber-300 border-amber-500/30 bg-amber-500/10",
  ELEVATED: "text-orange-300 border-orange-500/30 bg-orange-500/10",
  HIGH: "text-rose-300 border-rose-500/30 bg-rose-500/10",
};

export function IntegrityScore({ fusion }: IntegrityScoreProps) {
  if (!fusion) {
    return (
      <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
        <h2 className="text-lg font-semibold text-white">Integrity</h2>
        <p className="mt-2 text-sm text-slate-400">Evidence Fusion analysis has not completed.</p>
      </section>
    );
  }

  const score = fusion.evidence_integrity_score;
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
      <h2 className="text-lg font-semibold text-white">Integrity</h2>
      <div className="mt-4 flex flex-col items-center gap-4 sm:flex-row sm:items-center sm:gap-8">
        <div className="relative h-32 w-32">
          <svg className="h-32 w-32 -rotate-90" viewBox="0 0 120 120">
            <circle cx="60" cy="60" r={radius} fill="none" strokeWidth="8" className="text-slate-800" />
            <circle
              cx="60"
              cy="60"
              r={radius}
              fill="none"
              strokeWidth="8"
              strokeLinecap="round"
              className={score >= 70 ? "text-emerald-400" : score >= 45 ? "text-amber-400" : "text-rose-400"}
              strokeDasharray={circumference}
              strokeDashoffset={offset}
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-2xl font-bold text-white">{score.toFixed(1)}</span>
          </div>
        </div>
        <div className="space-y-2 text-center sm:text-left">
          <span
            className={`inline-block rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wider ${
              RISK_COLORS[fusion.risk_level] ?? RISK_COLORS.HIGH
            }`}
          >
            {fusion.risk_level} risk
          </span>
          <p className="text-sm text-slate-300">Confidence: {fusion.confidence.toFixed(1)}%</p>
          <p className="text-xs text-slate-400">{fusion.explanation}</p>
        </div>
      </div>
    </section>
  );
}
