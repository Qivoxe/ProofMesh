import { useCallback, useState } from "react";

import { AnalysisProgress } from "./components/AnalysisProgress";
import { InvestigationResults } from "./pages/InvestigationResults";
import { LandingPage } from "./pages/LandingPage";
import type { InvestigationResponse } from "./types/investigation";
import type { AnalysisResults } from "./types/analysis";
import type { EvidenceGraphResponse } from "./types/graph";
import {
  analyzeCopyMove,
  analyzeDocument,
  analyzeFusion,
  analyzeImage,
  analyzeMetadata,
  analyzeOCR,
  getEvidenceGraph,
  uploadEvidence,
} from "./services/api";

type AppStatus = "idle" | "uploading" | "analyzing" | "complete" | "error";

interface InvestigationState {
  response: InvestigationResponse;
  file: File;
  results: AnalysisResults;
  graph: EvidenceGraphResponse | null;
  analysisErrors: string[];
  status: AppStatus;
}

const EMPTY_RESULTS: AnalysisResults = {};

export function App() {
  const [investigation, setInvestigation] = useState<InvestigationState | null>(null);
  const [currentStep, setCurrentStep] = useState<string>("");

  const runAnalyses = useCallback(async (investigationId: string) => {
    const results: AnalysisResults = {};
    const errors: string[] = [];

    const steps: { key: keyof AnalysisResults; label: string; fn: () => Promise<any> }[] = [
      { key: "metadata", label: "Metadata", fn: () => analyzeMetadata(investigationId) },
      { key: "image", label: "Image Forensics", fn: () => analyzeImage(investigationId) },
      { key: "copyMove", label: "Copy-Move", fn: () => analyzeCopyMove(investigationId) },
      { key: "ocr", label: "OCR", fn: () => analyzeOCR(investigationId) },
      { key: "document", label: "Document Analysis", fn: () => analyzeDocument(investigationId) },
      { key: "fusion", label: "Evidence Fusion", fn: () => analyzeFusion(investigationId) },
    ];

    for (const step of steps) {
      setCurrentStep(step.label);
      try {
        results[step.key] = await step.fn();
      } catch (error) {
        errors.push(`${step.label}: ${error instanceof Error ? error.message : "Unknown error"}`);
      }
    }

    setCurrentStep("Evidence Graph");
    let graph: EvidenceGraphResponse | null = null;
    try {
      graph = await getEvidenceGraph(investigationId);
    } catch (error) {
      errors.push(`Evidence Graph: ${error instanceof Error ? error.message : "Unknown error"}`);
    }

    setInvestigation((prev) =>
      prev
        ? {
            ...prev,
            results,
            graph,
            analysisErrors: errors,
            status: errors.length > 0 ? "error" : "complete",
          }
        : prev,
    );
    setCurrentStep("");
  }, []);

  const handleUpload = useCallback(async (file: File) => {
    setCurrentStep("Uploading");
    setInvestigation({
      response: null as unknown as InvestigationResponse,
      file,
      results: EMPTY_RESULTS,
      graph: null,
      analysisErrors: [],
      status: "uploading",
    });

    try {
      const response = await uploadEvidence(file);
      setInvestigation({
        response,
        file,
        results: EMPTY_RESULTS,
        graph: null,
        analysisErrors: [],
        status: "analyzing",
      });
      await runAnalyses(response.investigation_id);
    } catch (error) {
      setInvestigation((prev) =>
        prev
          ? {
              ...prev,
              status: "error",
              analysisErrors: [error instanceof Error ? error.message : "Upload failed"],
            }
          : prev,
      );
      setCurrentStep("");
    }
  }, [runAnalyses]);

  const handleReset = useCallback(() => {
    setInvestigation(null);
    setCurrentStep("");
  }, []);

  if (!investigation) {
    return <LandingPage onUpload={handleUpload} />;
  }

  if (investigation.status === "analyzing" || currentStep) {
    return <AnalysisProgress currentStep={currentStep} />;
  }

  if (investigation.status === "complete" || investigation.status === "error") {
    if (!investigation.response) {
      return (
        <div className="flex min-h-screen items-center justify-center text-slate-300">
          <p>Preparing investigation…</p>
        </div>
      );
    }
    return (
      <InvestigationResults
        investigation={investigation}
        onReset={handleReset}
      />
    );
  }

  return <LandingPage onUpload={handleUpload} />;
}
