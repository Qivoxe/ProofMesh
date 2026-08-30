import type { OCRBlock } from "../types/analysis";

interface OCRPanelProps {
  ocr: {
    text: string;
    blocks: OCRBlock[];
    average_confidence: number;
    findings: { kind: string; message: string }[];
  };
}

export function OCRPanel({ ocr }: OCRPanelProps) {
  const unavailable = ocr.findings.some((f) => f.kind === "OCR unavailable");

  if (unavailable) {
    return (
      <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
        <h2 className="text-lg font-semibold text-white">OCR</h2>
        <p className="mt-4 rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-200">
          OCR unavailable — Tesseract OCR is not installed or is not available on the server PATH.
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
      <h2 className="text-lg font-semibold text-white">OCR</h2>
      <p className="mt-1 text-xs text-slate-400">
        Average confidence: {ocr.average_confidence.toFixed(1)}% · {ocr.blocks.length} blocks
      </p>
      <div className="mt-4 max-h-96 overflow-y-auto rounded-xl border border-slate-800 bg-slate-950/50 p-4">
        <pre className="whitespace-pre-wrap text-sm text-slate-300">{ocr.text || "No text extracted."}</pre>
      </div>
    </section>
  );
}
