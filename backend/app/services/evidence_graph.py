"""NetworkX construction of evidence-backed investigation graphs."""

from __future__ import annotations

from typing import Any

import networkx as nx

from app.models.investigation import EvidenceGraphEdge, EvidenceGraphNode, EvidenceGraphResponse
from app.services.copy_move_detection import analyze_copy_move
from app.services.document_forensics import analyze_document_forensics
from app.services.evidence_fusion import fuse_evidence
from app.services.evidence_storage import investigation_file
from app.services.image_forensics import IMAGE_SUFFIXES, analyze_image_forensics
from app.services.metadata_analysis import analyze_metadata
from app.services.ocr import analyze_ocr


def _add_node(
    graph: nx.MultiDiGraph,
    investigation_id: str,
    node_id: str,
    node_type: str,
    label: str,
    evidence_reference: str,
) -> None:
    """Add a node that always carries a concrete reference to stored evidence."""
    graph.add_node(
        node_id,
        node_type=node_type,
        label=label,
        investigation_id=investigation_id,
        evidence_reference=evidence_reference,
    )


def _add_edge(graph: nx.MultiDiGraph, source: str, target: str, relationship: str) -> None:
    graph.add_edge(source, target, relationship=relationship)


def _timestamps(metadata: dict[str, Any]) -> list[tuple[str, str]]:
    image_timestamps = metadata.get("timestamps")
    if isinstance(image_timestamps, dict):
        return [(str(name), str(value)) for name, value in sorted(image_timestamps.items()) if value]
    return [
        (name, str(metadata[name]))
        for name in ("creation_date", "modification_date")
        if metadata.get(name)
    ]


def build_evidence_graph(investigation_id: str) -> EvidenceGraphResponse:
    """Build a stable graph of actual analysis observations for an investigation."""
    artifact = investigation_file(investigation_id)
    is_image = artifact.suffix.lower() in IMAGE_SUFFIXES
    metadata = analyze_metadata(investigation_id)
    image = analyze_image_forensics(investigation_id) if is_image else None
    copy_move = analyze_copy_move(investigation_id) if is_image else None
    ocr = analyze_ocr(investigation_id)
    document = analyze_document_forensics(investigation_id)
    fusion = fuse_evidence(metadata, image, copy_move, ocr, document)

    graph = nx.MultiDiGraph()
    artifact_id = "artifact:0"
    _add_node(graph, investigation_id, artifact_id, "Artifact", artifact.name, f"artifact:{investigation_id}")

    metadata_id = "metadata:0"
    _add_node(graph, investigation_id, metadata_id, "Metadata", "Extracted metadata", "metadata:analysis")
    _add_edge(graph, artifact_id, metadata_id, "HAS_METADATA")
    timestamp_ids: list[str] = []
    for index, (name, value) in enumerate(_timestamps(metadata.metadata)):
        timestamp_id = f"timestamp:{index}"
        timestamp_ids.append(timestamp_id)
        _add_node(graph, investigation_id, timestamp_id, "Timestamp", f"{name}: {value}", f"metadata:timestamp:{name}")
        _add_edge(graph, metadata_id, timestamp_id, "CONTAINS")

    metadata_finding_ids: list[str] = []
    for index, finding in enumerate(metadata.findings):
        finding_id = f"finding:metadata:{index}"
        metadata_finding_ids.append(finding_id)
        _add_node(graph, investigation_id, finding_id, "Finding", finding.kind, f"metadata:finding:{index}")
        _add_edge(graph, metadata_id, finding_id, "INDICATES")
        if "timestamp" in finding.kind.lower():
            for timestamp_id in timestamp_ids:
                _add_edge(graph, timestamp_id, finding_id, "CONFLICTS_WITH")

    image_signal_ids: list[str] = []
    image_region_ids: list[str] = []
    if image is not None:
        for index, signal in enumerate(image.signals):
            signal_id = f"image-signal:{index}"
            image_signal_ids.append(signal_id)
            _add_node(graph, investigation_id, signal_id, "Image Signal", signal.kind, f"image:signal:{index}")
            _add_edge(graph, artifact_id, signal_id, "CONTAINS")
        for index, region in enumerate(image.suspicious_regions):
            region_id = f"suspicious-region:image:{index}"
            image_region_ids.append(region_id)
            _add_node(
                graph,
                investigation_id,
                region_id,
                "Suspicious Region",
                f"Image region at ({region.x}, {region.y})",
                f"image:region:{index}",
            )
            _add_edge(graph, artifact_id, region_id, "CONTAINS")
            for signal_id in image_signal_ids:
                _add_edge(graph, signal_id, region_id, "INDICATES")

    if copy_move is not None:
        for index, signal in enumerate(copy_move.signals):
            signal_id = f"image-signal:copy-move:{index}"
            image_signal_ids.append(signal_id)
            _add_node(graph, investigation_id, signal_id, "Image Signal", signal.kind, f"copy-move:signal:{index}")
            _add_edge(graph, artifact_id, signal_id, "CONTAINS")
        for index, region in enumerate(copy_move.suspicious_regions):
            region_id = f"suspicious-region:copy-move:{index}"
            _add_node(
                graph,
                investigation_id,
                region_id,
                "Suspicious Region",
                f"Copy-move region at ({region.x}, {region.y})",
                f"copy-move:region:{index}",
            )
            _add_edge(graph, artifact_id, region_id, "CONTAINS")
            for signal_id in image_signal_ids:
                _add_edge(graph, signal_id, region_id, "INDICATES")

    ocr_node_ids: list[str] = []
    for index, block in enumerate(ocr.blocks):
        text_id = f"ocr-text:{index}"
        ocr_node_ids.append(text_id)
        _add_node(graph, investigation_id, text_id, "OCR Text", block.text, f"ocr:block:{index}")
        _add_edge(graph, artifact_id, text_id, "CONTAINS")

    document_signal_ids: list[str] = []
    for index, finding in enumerate(document.findings):
        signal_id = f"document-signal:{index}"
        document_signal_ids.append(signal_id)
        _add_node(graph, investigation_id, signal_id, "Document Signal", finding.kind, f"document:finding:{index}")
        _add_edge(graph, artifact_id, signal_id, "CONTAINS")
        for block_index in finding.block_indexes:
            if block_index < len(ocr_node_ids):
                _add_edge(graph, ocr_node_ids[block_index], signal_id, "SUPPORTS")

    for relationship in document.ocr_region_relationships:
        if (
            relationship.ocr_block_index < len(ocr_node_ids)
            and relationship.suspicious_region_index < len(image_region_ids)
        ):
            _add_edge(
                graph,
                ocr_node_ids[relationship.ocr_block_index],
                image_region_ids[relationship.suspicious_region_index],
                "OVERLAPS",
            )

    for index, fusion_finding in enumerate(fusion.findings):
        finding_id = f"finding:fusion:{index}"
        _add_node(
            graph,
            investigation_id,
            finding_id,
            "Finding",
            f"{fusion_finding.category}: {fusion_finding.kind}",
            f"fusion:finding:{index}",
        )
        _add_edge(graph, artifact_id, finding_id, "CONTAINS")
        if fusion_finding.category == "metadata":
            _add_edge(graph, metadata_id, finding_id, "SUPPORTS")
        elif fusion_finding.category == "image":
            for signal_id in image_signal_ids:
                _add_edge(graph, signal_id, finding_id, "SUPPORTS")
        elif fusion_finding.category == "document":
            for signal_id in document_signal_ids:
                _add_edge(graph, signal_id, finding_id, "SUPPORTS")
        elif fusion_finding.category == "ocr":
            for text_id in ocr_node_ids:
                _add_edge(graph, text_id, finding_id, "SUPPORTS")

    nodes = [
        EvidenceGraphNode(id=node_id, **attributes)
        for node_id, attributes in sorted(graph.nodes(data=True), key=lambda item: item[0])
    ]
    edges = [
        EvidenceGraphEdge(source=source, target=target, relationship=attributes["relationship"])
        for source, target, _, attributes in sorted(
            graph.edges(keys=True, data=True),
            key=lambda edge: (edge[0], edge[1], edge[3]["relationship"], edge[2]),
        )
    ]
    return EvidenceGraphResponse(nodes=nodes, edges=edges)
