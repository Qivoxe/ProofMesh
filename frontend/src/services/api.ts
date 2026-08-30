import type {
  HealthResponse,
} from "../types/health";
import type { InvestigationResponse } from "../types/investigation";
import type {
  MetadataAnalysisResponse,
  ImageForensicsResponse,
  CopyMoveAnalysisResponse,
  OCRAnalysisResponse,
  DocumentForensicsResponse,
  EvidenceFusionResponse,
} from "../types/analysis";
import type { EvidenceGraphResponse } from "../types/graph";

const apiBaseUrl = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

async function handleResponse<T>(response: Response, fallbackMessage: string): Promise<T> {
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? fallbackMessage);
  }
  return response.json() as Promise<T>;
}

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${apiBaseUrl}/health`);
  return handleResponse<HealthResponse>(response, `Health check failed with status ${response.status}`);
}

export async function uploadEvidence(file: File): Promise<InvestigationResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${apiBaseUrl}/api/v1/investigations`, {
    method: "POST",
    body: formData,
  });

  return handleResponse<InvestigationResponse>(response, "Unable to upload evidence.");
}

export async function analyzeMetadata(investigationId: string): Promise<MetadataAnalysisResponse> {
  const response = await fetch(
    `${apiBaseUrl}/api/v1/investigations/${encodeURIComponent(investigationId)}/analyze/metadata`,
    { method: "POST" },
  );
  return handleResponse<MetadataAnalysisResponse>(response, "Metadata analysis failed.");
}

export async function analyzeImage(investigationId: string): Promise<ImageForensicsResponse> {
  const response = await fetch(
    `${apiBaseUrl}/api/v1/investigations/${encodeURIComponent(investigationId)}/analyze/image`,
    { method: "POST" },
  );
  return handleResponse<ImageForensicsResponse>(response, "Image forensics analysis failed.");
}

export async function analyzeCopyMove(investigationId: string): Promise<CopyMoveAnalysisResponse> {
  const response = await fetch(
    `${apiBaseUrl}/api/v1/investigations/${encodeURIComponent(investigationId)}/analyze/copy-move`,
    { method: "POST" },
  );
  return handleResponse<CopyMoveAnalysisResponse>(response, "Copy-move analysis failed.");
}

export async function analyzeOCR(investigationId: string): Promise<OCRAnalysisResponse> {
  const response = await fetch(
    `${apiBaseUrl}/api/v1/investigations/${encodeURIComponent(investigationId)}/analyze/ocr`,
    { method: "POST" },
  );
  return handleResponse<OCRAnalysisResponse>(response, "OCR analysis failed.");
}

export async function analyzeDocument(investigationId: string): Promise<DocumentForensicsResponse> {
  const response = await fetch(
    `${apiBaseUrl}/api/v1/investigations/${encodeURIComponent(investigationId)}/analyze/document`,
    { method: "POST" },
  );
  return handleResponse<DocumentForensicsResponse>(response, "Document forensics analysis failed.");
}

export async function analyzeFusion(investigationId: string): Promise<EvidenceFusionResponse> {
  const response = await fetch(
    `${apiBaseUrl}/api/v1/investigations/${encodeURIComponent(investigationId)}/analyze/fusion`,
    { method: "POST" },
  );
  return handleResponse<EvidenceFusionResponse>(response, "Evidence fusion analysis failed.");
}

export async function getEvidenceGraph(investigationId: string): Promise<EvidenceGraphResponse> {
  const response = await fetch(
    `${apiBaseUrl}/api/v1/investigations/${encodeURIComponent(investigationId)}/graph`,
  );
  return handleResponse<EvidenceGraphResponse>(response, "Evidence graph retrieval failed.");
}
