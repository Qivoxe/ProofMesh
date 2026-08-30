import type {
  MetadataFinding,
  DocumentForensicsFinding,
  NormalizedFusionSignal,
  OCRFinding,
} from "../types/analysis";

interface UnifiedFinding {
  source: string;
  kind: string;
  message: string;
  confidence: number;
  severity: "high" | "medium" | "low" | "info";
}

interface FindingsListProps {
  metadata: { findings: MetadataFinding[] } | undefined;
  document: { findings: DocumentForensicsFinding[] } | undefined;
  fusion: { findings: NormalizedFusionSignal[] } | undefined;
  ocr: { findings: OCRFinding[] } | undefined;
}

function toSeverity(confidence: number, kind: string): UnifiedFinding["severity"] {
  if (kind.toLowerCase().includes("unavailable")) return "info";
  if (kind.toLowerCase().includes("inconsistency")) return "high";
  if (confidence > 0.7) return "high";
  if (confidence > 0.4) return "medium";
  return "low";
}

const severityStyles: Record<string, string> = {
  high: "border-rose-500/30 bg-rose-500/10 text-rose-300",
  medium: "border-amber-500/30 bg-amber-500/10 text-amber-300",
  low: "border-slate-700 bg-slate-800/50 text-slate-300",
  info: "border-slate-700 bg-slate-800/30 text-slate-400",
};

export function FindingsList({ metadata, document, fusion, ocr }: FindingsListProps) {
  const findings: UnifiedFinding[] = [];

  metadata?.findings.forEach((f) => {
    findings.push({
      source: "Metadata",
      kind: f.kind,
      message: f.message,
      confidence: f.heuristic ? 0.6 : 0.3,
      severity: toSeverity(f.heuristic ? 0.6 : 0.3, f.kind),
    });
  });

  document?.findings.forEach((f) => {
    findings.push({
      source: "Document",
      kind: f.kind,
      message: f.message,
      confidence: f.confidence,
      severity: toSeverity(f.confidence, f.kind),
    });
  });

  fusion?.findings.forEach((f) => {
    findings.push({
      source: f.category,
      kind: f.kind,
      message: f.message,
      confidence: f.normalized_concern,
      severity: toSeverity(f.normalized_concern, f.kind),
    });
  });

  ocr?.findings.forEach((f) => {
    findings.push({
      source: "OCR",
      kind: f.kind,
      message: f.message,
      confidence: f.kind === "OCR unavailable" ? 0 : 0.5,
      severity: toSeverity(f.kind === "OCR unavailable" ? 0 : 0.5, f.kind),
    });
  });

  findings.sort((a, b) => b.confidence - a.confidence);

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
      <h2 className="text-lg font-semibold text-white">Findings</h2>
      {findings.length === 0 ? (
        <p className="mt-2 text-sm text-slate-400">No findings were returned by the analysis pipeline.</p>
      ) : (
        <ul className="mt-4 space-y-3">
          {findings.map((finding, index) => (
            <li key={`${finding.source}-${finding.kind}-${index}`} className={`rounded-xl border p-4 ${severityStyles[finding.severity]}`}>
              <div className="flex items-center justify-between gap-4">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">{finding.source}</span>
                <span className="text-xs text-slate-400">{(finding.confidence * 100).toFixed(1)}%</span>
              </div>
              <p className="mt-1 text-sm font-medium">{finding.kind}</p>
              <p className="mt-1 text-xs opacity-90">{finding.message}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
