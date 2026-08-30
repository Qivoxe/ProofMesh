export interface MetadataFinding {
  kind: string;
  message: string;
  heuristic?: boolean;
}

export interface MetadataAnalysisResponse {
  investigation_id: string;
  file_type: string;
  metadata: Record<string, unknown>;
  findings: MetadataFinding[];
}

export interface ImageForensicsSignal {
  kind: string;
  message: string;
  confidence: number;
  details?: Record<string, unknown>;
}

export interface SuspiciousRegion {
  x: number;
  y: number;
  width: number;
  height: number;
  confidence: number;
  reason: string;
}

export interface ImageForensicsResponse {
  signals: ImageForensicsSignal[];
  suspicious_regions: SuspiciousRegion[];
  overall_anomaly_score: number;
}

export interface CopyMoveAnalysisResponse {
  signals: ImageForensicsSignal[];
  suspicious_regions: SuspiciousRegion[];
}

export interface OCRBlock {
  text: string;
  confidence: number;
  x: number;
  y: number;
  width: number;
  height: number;
  page: number;
}

export interface OCRFinding {
  kind: string;
  message: string;
}

export interface OCRAnalysisResponse {
  text: string;
  blocks: OCRBlock[];
  average_confidence: number;
  findings: OCRFinding[];
}

export interface DocumentForensicsFinding {
  kind: string;
  message: string;
  confidence: number;
  page?: number | null;
  block_indexes: number[];
  details?: Record<string, unknown>;
}

export interface OCRRegionRelationship {
  ocr_block_index: number;
  suspicious_region_index: number;
  page: number;
  overlap_ratio: number;
  message: string;
}

export interface DocumentForensicsResponse {
  findings: DocumentForensicsFinding[];
  ocr_region_relationships: OCRRegionRelationship[];
}

export interface NormalizedFusionSignal {
  category: string;
  kind: string;
  message: string;
  normalized_concern: number;
}

export interface EvidenceFusionResponse {
  evidence_integrity_score: number;
  risk_level: string;
  findings: NormalizedFusionSignal[];
  normalized_signals: NormalizedFusionSignal[];
  category_concern_scores: Record<string, number>;
  weights: Record<string, number>;
  confidence: number;
  explanation: string;
}

export interface AnalysisResults {
  metadata?: MetadataAnalysisResponse;
  image?: ImageForensicsResponse;
  copyMove?: CopyMoveAnalysisResponse;
  ocr?: OCRAnalysisResponse;
  document?: DocumentForensicsResponse;
  fusion?: EvidenceFusionResponse;
}
