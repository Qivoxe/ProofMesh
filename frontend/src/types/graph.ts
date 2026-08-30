export interface EvidenceGraphNode {
  id: string;
  node_type: string;
  label: string;
  investigation_id: string;
  evidence_reference: string;
}

export interface EvidenceGraphEdge {
  source: string;
  target: string;
  relationship: string;
}

export interface EvidenceGraphResponse {
  nodes: EvidenceGraphNode[];
  edges: EvidenceGraphEdge[];
}
