import type {
  ImageForensicsResponse,
  CopyMoveAnalysisResponse,
  MetadataAnalysisResponse,
  OCRAnalysisResponse,
  DocumentForensicsResponse,
} from "../types/analysis";

interface ForensicSignalsProps {
  metadata: MetadataAnalysisResponse | undefined;
  image: ImageForensicsResponse | undefined;
  copyMove: CopyMoveAnalysisResponse | undefined;
  ocr: OCRAnalysisResponse | undefined;
  document: DocumentForensicsResponse | undefined;
}

interface SignalCardProps {
  title: string;
  children: React.ReactNode;
}

function SignalCard({ title, children }: SignalCardProps) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
      <h3 className="text-sm font-semibold text-slate-300">{title}</h3>
      <div className="mt-2 space-y-1 text-xs text-slate-400">{children}</div>
    </div>
  );
}

export function ForensicSignals({ metadata, image, copyMove, ocr, document }: ForensicSignalsProps) {
  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
      <h2 className="text-lg font-semibold text-white">Forensic Signals</h2>
      <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <SignalCard title="Metadata">
          <p>Findings: {metadata?.findings.length ?? 0}</p>
          {metadata?.metadata?.software ? <p>Software: {String(metadata.metadata.software)}</p> : null}
          {metadata?.metadata?.author ? <p>Author: {String(metadata.metadata.author)}</p> : null}
          {metadata?.metadata?.producer ? <p>Producer: {String(metadata.metadata.producer)}</p> : null}
        </SignalCard>

        <SignalCard title="Image Forensics">
          <p>Anomaly score: {image ? `${(image.overall_anomaly_score * 100).toFixed(1)}%` : "N/A"}</p>
          <p>Signals: {image?.signals.length ?? 0}</p>
          <p>Suspicious regions: {image?.suspicious_regions.length ?? 0}</p>
          {image?.signals.map((signal, index) => (
            <p key={index} className="truncate" title={signal.message}>
              • {signal.kind}
            </p>
          ))}
        </SignalCard>

        <SignalCard title="Copy-Move">
          <p>Signals: {copyMove?.signals.length ?? 0}</p>
          <p>Suspicious regions: {copyMove?.suspicious_regions.length ?? 0}</p>
          {copyMove?.signals.map((signal, index) => (
            <p key={index} className="truncate" title={signal.message}>
              • {signal.kind}
            </p>
          ))}
        </SignalCard>

        <SignalCard title="OCR">
          <p>Average confidence: {ocr ? `${ocr.average_confidence.toFixed(1)}%` : "N/A"}</p>
          <p>Blocks: {ocr?.blocks.length ?? 0}</p>
          <p>Findings: {ocr?.findings.length ?? 0}</p>
          {ocr?.findings.map((finding, index) => (
            <p key={index}>{finding.kind}</p>
          ))}
        </SignalCard>

        <SignalCard title="Document">
          <p>Findings: {document?.findings.length ?? 0}</p>
          <p>OCR region relationships: {document?.ocr_region_relationships.length ?? 0}</p>
          {document?.findings.slice(0, 3).map((finding, index) => (
            <p key={index} className="truncate" title={finding.message}>
              • {finding.kind}
            </p>
          ))}
        </SignalCard>
      </div>
    </section>
  );
}
