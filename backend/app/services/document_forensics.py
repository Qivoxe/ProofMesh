"""Heuristic document-layout consistency analysis built on OCR geometry.

OCR coordinates are estimates, and layout variation can be intentional. The
signals here identify areas for review; they do not identify fonts or establish
that a document was altered.
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np
from fastapi import HTTPException, status

from app.models.investigation import (
    DocumentForensicsFinding,
    DocumentForensicsResponse,
    OCRAnalysisResponse,
    OCRBlock,
    OCRRegionRelationship,
)
from app.services.evidence_storage import investigation_file
from app.services.image_forensics import analyze_image_forensics
from app.services.ocr import analyze_ocr


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}
MAX_LAYOUT_FINDINGS = 20


def _lines(blocks: list[OCRBlock]) -> dict[int, list[list[tuple[int, OCRBlock]]]]:
    """Group word boxes into approximate visual lines, separately for each page."""
    pages: dict[int, list[tuple[int, OCRBlock]]] = defaultdict(list)
    for index, block in enumerate(blocks):
        pages[block.page].append((index, block))

    result: dict[int, list[list[tuple[int, OCRBlock]]]] = {}
    for page, page_blocks in pages.items():
        page_lines: list[list[tuple[int, OCRBlock]]] = []
        for item in sorted(page_blocks, key=lambda item: (item[1].y, item[1].x)):
            _, block = item
            center = block.y + block.height / 2
            if page_lines:
                previous = page_lines[-1]
                previous_center = float(np.median([item[1].y + item[1].height / 2 for item in previous]))
                threshold = max(8.0, float(np.median([item[1].height for item in previous])) * 0.75)
                if abs(center - previous_center) <= threshold:
                    previous.append(item)
                    continue
            page_lines.append([item])
        result[page] = [sorted(line, key=lambda item: item[1].x) for line in page_lines]
    return result


def _layout_finding(
    message: str,
    page: int,
    block_indexes: list[int],
    analysis: str,
    confidence: float,
    **details: float | int,
) -> DocumentForensicsFinding:
    return DocumentForensicsFinding(
        kind="Text rendering/layout inconsistency",
        message=message,
        confidence=round(min(1.0, confidence), 3),
        page=page,
        block_indexes=block_indexes,
        details={"analysis": analysis, **details},
    )


def _layout_findings(blocks: list[OCRBlock]) -> list[DocumentForensicsFinding]:
    findings: list[DocumentForensicsFinding] = []
    page_lines = _lines(blocks)
    for page, lines in page_lines.items():
        gaps: list[tuple[float, list[int]]] = []
        for line in lines:
            for (left_index, left), (right_index, right) in zip(line, line[1:]):
                gap = right.x - (left.x + left.width)
                if gap >= 0:
                    gaps.append((float(gap), [left_index, right_index]))
        if len(gaps) >= 3:
            baseline = float(np.percentile([gap for gap, _ in gaps], 25))
            threshold = max(20.0, baseline * 3 + 10)
            for gap, indexes in gaps:
                if gap > threshold:
                    findings.append(_layout_finding(
                        "Unusual spacing between OCR text blocks may indicate a text rendering/layout inconsistency.",
                        page,
                        indexes,
                        "unusual_spacing",
                        min(0.95, gap / (threshold * 2)),
                        gap=round(gap, 1),
                        expected_gap_upper_bound=round(threshold, 1),
                    ))

        if len(lines) >= 3:
            left_edges = np.asarray([min(block.x for _, block in line) for line in lines], dtype=float)
            baseline = float(np.median(left_edges))
            threshold = max(20.0, float(np.median([max(block.width for _, block in line) for line in lines])) * 0.75)
            for line, left in zip(lines, left_edges):
                if abs(left - baseline) > threshold:
                    findings.append(_layout_finding(
                        "A line begins at an unusual horizontal position relative to nearby OCR lines.",
                        page,
                        [index for index, _ in line],
                        "alignment_inconsistency",
                        min(0.9, abs(left - baseline) / (threshold * 2)),
                        left_edge=round(float(left), 1),
                        baseline_left_edge=round(baseline, 1),
                    ))

            densities: list[float] = []
            for line in lines:
                left = min(block.x for _, block in line)
                right = max(block.x + block.width for _, block in line)
                densities.append(sum(block.width for _, block in line) / max(1, right - left))
            baseline = float(np.median(densities))
            for line, density in zip(lines, densities):
                if abs(density - baseline) > 0.35:
                    findings.append(_layout_finding(
                        "This OCR line has inconsistent text density compared with nearby lines.",
                        page,
                        [index for index, _ in line],
                        "inconsistent_text_density",
                        min(0.9, abs(density - baseline)),
                        line_density=round(density, 3),
                        baseline_density=round(baseline, 3),
                    ))

        page_items = [(index, block) for line in lines for index, block in line]
        if len(page_items) >= 4:
            centers = np.asarray([[block.x + block.width / 2, block.y + block.height / 2] for _, block in page_items])
            nearest = np.asarray([
                np.min(np.linalg.norm(centers[index] - np.delete(centers, index, axis=0), axis=1))
                for index in range(len(centers))
            ])
            threshold = max(80.0, float(np.median(nearest)) * 2.5)
            for (block_index, _), distance in zip(page_items, nearest):
                if distance > threshold:
                    findings.append(_layout_finding(
                        "An OCR text block is unusually isolated from the surrounding text layout.",
                        page,
                        [block_index],
                        "unusual_text_positioning",
                        min(0.9, distance / (threshold * 2)),
                        nearest_text_distance=round(float(distance), 1),
                    ))
    return findings


def _duplicate_findings(blocks: list[OCRBlock]) -> list[DocumentForensicsFinding]:
    grouped: dict[tuple[int, str], list[int]] = defaultdict(list)
    for index, block in enumerate(blocks):
        normalized = " ".join(block.text.lower().split())
        if len(normalized) >= 4:
            grouped[(block.page, normalized)].append(index)
    findings: list[DocumentForensicsFinding] = []
    for (page, text), indexes in grouped.items():
        if len(indexes) > 1:
            findings.append(DocumentForensicsFinding(
                kind="Duplicated OCR text",
                message="Repeated OCR text was found at separate positions; repeated wording can be intentional and should be reviewed in context.",
                confidence=round(min(0.85, 0.35 + 0.15 * len(indexes)), 3),
                page=page,
                block_indexes=indexes,
                details={"normalized_text": text, "occurrence_count": len(indexes)},
            ))
    return findings


def _relationships(blocks: list[OCRBlock], regions) -> tuple[list[OCRRegionRelationship], list[DocumentForensicsFinding]]:
    relationships: list[OCRRegionRelationship] = []
    findings: list[DocumentForensicsFinding] = []
    for block_index, block in enumerate(blocks):
        if block.page != 1:
            continue
        block_area = block.width * block.height
        for region_index, region in enumerate(regions):
            overlap_width = max(0, min(block.x + block.width, region.x + region.width) - max(block.x, region.x))
            overlap_height = max(0, min(block.y + block.height, region.y + region.height) - max(block.y, region.y))
            overlap = overlap_width * overlap_height
            if not overlap:
                continue
            ratio = overlap / block_area
            relationships.append(OCRRegionRelationship(
                ocr_block_index=block_index,
                suspicious_region_index=region_index,
                page=block.page,
                overlap_ratio=round(ratio, 3),
                message="OCR text overlaps a potentially anomalous image region and may warrant joint review.",
            ))
            findings.append(DocumentForensicsFinding(
                kind="Suspicious OCR/image overlap",
                message="An OCR text block overlaps a potentially anomalous image region; this is a review relationship, not proof of document alteration.",
                confidence=round(min(0.95, 0.35 + ratio * 0.6 + region.confidence * 0.2), 3),
                page=block.page,
                block_indexes=[block_index],
                details={"suspicious_region_index": region_index, "overlap_ratio": round(ratio, 3)},
            ))
    return relationships, findings


def analyze_document_forensics(investigation_id: str) -> DocumentForensicsResponse:
    """Assess OCR geometry and associate page-one image regions with OCR boxes."""
    path = investigation_file(investigation_id)
    suffix = path.suffix.lower()
    if suffix not in IMAGE_SUFFIXES | {".pdf"}:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Document analysis supports only PNG, JPG, JPEG, and PDF evidence.")

    ocr_result: OCRAnalysisResponse = analyze_ocr(investigation_id)
    findings = [DocumentForensicsFinding(
        kind=finding.kind,
        message=finding.message,
        confidence=0.0,
        details={"source": "ocr"},
    ) for finding in ocr_result.findings if finding.kind == "OCR unavailable"]
    findings.extend(_layout_findings(ocr_result.blocks))
    findings.extend(_duplicate_findings(ocr_result.blocks))

    relationships: list[OCRRegionRelationship] = []
    if suffix in IMAGE_SUFFIXES:
        image_result = analyze_image_forensics(investigation_id)
        relationships, overlap_findings = _relationships(ocr_result.blocks, image_result.suspicious_regions)
        findings.extend(overlap_findings)
    elif ocr_result.blocks:
        findings.append(DocumentForensicsFinding(
            kind="Image-region relationship unavailable",
            message="Suspicious image-region overlap is not evaluated for multi-page PDF OCR coordinates.",
            confidence=0.0,
        ))

    return DocumentForensicsResponse(
        findings=findings[:MAX_LAYOUT_FINDINGS],
        ocr_region_relationships=relationships,
    )
