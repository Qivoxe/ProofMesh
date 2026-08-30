import type { InvestigationResponse } from "../types/investigation";
import type { AnalysisResults } from "../types/analysis";
import type { EvidenceGraphResponse } from "../types/graph";

import { EvidenceInfo } from "../components/EvidenceInfo";
import { IntegrityScore } from "../components/IntegrityScore";
import { FindingsList } from "../components/FindingsList";
import { ForensicSignals } from "../components/ForensicSignals";
import { ImageViewer } from "../components/ImageViewer";
import { OCRPanel } from "../components/OCRPanel";
import { EvidenceGraph } from "../components/EvidenceGraph";

interface InvestigationResultsProps {
  investigation: {
    response: InvestigationResponse;
    file: File;
    results: AnalysisResults;
    graph: EvidenceGraphResponse | null;
    analysisErrors: string[];
  };
  onReset: () => void;
}

export function InvestigationResults({ investigation, onReset }: InvestigationResultsProps) {
  const { response, file, results, graph, analysisErrors } = investigation;

  const isImage = response.file_type.startsWith("image/");

  return (
    <div className="min-h-screen bg-slate-950 px-6 py-10">
      <div className="mx-auto max-w-5xl space-y-8">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-white">Investigation Results</h1>
          <button
            onClick={onReset}
            className="rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-sm font-semibold text-slate-300 transition hover:border-cyan-400 hover:text-cyan-300"
          >
            New Investigation
          </button>
        </div>

        {analysisErrors.length > 0 && (
          <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4">
            <h3 className="font-semibold text-rose-300">Analysis Warnings</h3>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-rose-200">
              {analysisErrors.map((err, index) => (
                <li key={index}>{err}</li>
              ))}
            </ul>
          </div>
        )}

        <EvidenceInfo response={response} />

        <IntegrityScore fusion={results.fusion} />

        <FindingsList
          metadata={results.metadata}
          document={results.document}
          fusion={results.fusion}
          ocr={results.ocr}
        />

        <ForensicSignals
          metadata={results.metadata}
          image={results.image}
          copyMove={results.copyMove}
          ocr={results.ocr}
          document={results.document}
        />

        {isImage && (
          <ImageViewer
            file={file}
            imageResults={results.image}
            copyMoveResults={results.copyMove}
            ocrBlocks={results.ocr?.blocks}
          />
        )}

        {results.ocr && <OCRPanel ocr={results.ocr} />}

        {graph && <EvidenceGraph graph={graph} />}
      </div>
    </div>
  );
}
