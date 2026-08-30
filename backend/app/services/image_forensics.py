"""Lightweight, explainable image-forensic heuristics.

The measurements in this module can highlight areas worth review.  They cannot
establish that an image has been manipulated, so all output is intentionally
phrased as a potential anomaly rather than proof.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from fastapi import HTTPException, status
from PIL import Image, ImageOps, UnidentifiedImageError

from app.models.investigation import ImageForensicsResponse, ImageForensicsSignal, SuspiciousRegion
from app.services.evidence_storage import investigation_file


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}
MAX_ANALYSIS_DIMENSION = 1600


def _load_image(path: Path) -> np.ndarray:
    """Load an evidence image as RGB while bounding analysis memory."""
    try:
        with Image.open(path) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            if max(image.size) > MAX_ANALYSIS_DIMENSION:
                scale = MAX_ANALYSIS_DIMENSION / max(image.size)
                image = image.resize(
                    (round(image.width * scale), round(image.height * scale)),
                    Image.Resampling.LANCZOS,
                )
            return np.asarray(image)
    except (UnidentifiedImageError, OSError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Image evidence could not be read.",
        ) from error


def _tile_means(values: np.ndarray, tile_size: int) -> tuple[np.ndarray, list[tuple[int, int, int, int]]]:
    """Return means for a complete image grid and the source bounds of each cell."""
    height, width = values.shape
    cells: list[tuple[int, int, int, int]] = []
    means: list[float] = []
    for y in range(0, height, tile_size):
        for x in range(0, width, tile_size):
            y_end, x_end = min(y + tile_size, height), min(x + tile_size, width)
            cells.append((x, y, x_end - x, y_end - y))
            means.append(float(values[y:y_end, x:x_end].mean()))
    return np.asarray(means, dtype=np.float32), cells


def _positive_outlier_scores(values: np.ndarray) -> np.ndarray:
    """Map positive local deviations to 0..1 without treating a normal texture as proof."""
    center = float(np.median(values))
    spread = max(float(np.std(values)), 1.0)
    return np.clip((values - center) / (spread * 2.5), 0.0, 1.0)


def _region_reason(noise_score: float, edge_score: float, compression_score: float) -> str:
    if compression_score >= max(noise_score, edge_score):
        return "Potentially manipulated region: Compression inconsistency."
    return "Potentially manipulated region: Local image anomaly."


def _build_regions(
    cells: list[tuple[int, int, int, int]],
    scores: np.ndarray,
    noise_scores: np.ndarray,
    edge_scores: np.ndarray,
    compression_scores: np.ndarray,
    tile_size: int,
    width: int,
    height: int,
) -> list[SuspiciousRegion]:
    candidates = [index for index, score in enumerate(scores) if score >= 0.55]
    if not candidates:
        return []

    # Grid cells only touch horizontally or vertically; grouping them avoids a
    # separate, opaque segmentation model.
    grid_width = (width + tile_size - 1) // tile_size
    candidate_set = set(candidates)
    groups: list[list[int]] = []
    while candidate_set:
        stack = [candidate_set.pop()]
        group: list[int] = []
        while stack:
            index = stack.pop()
            group.append(index)
            row, column = divmod(index, grid_width)
            for neighbor in (index - 1, index + 1, index - grid_width, index + grid_width):
                neighbor_row, neighbor_column = divmod(neighbor, grid_width) if neighbor >= 0 else (-1, -1)
                if (
                    neighbor in candidate_set
                    and 0 <= neighbor_row < (height + tile_size - 1) // tile_size
                    and abs(neighbor_column - column) + abs(neighbor_row - row) == 1
                ):
                    candidate_set.remove(neighbor)
                    stack.append(neighbor)
        groups.append(group)

    regions: list[SuspiciousRegion] = []
    for group in groups:
        group_cells = [cells[index] for index in group]
        x = min(cell[0] for cell in group_cells)
        y = min(cell[1] for cell in group_cells)
        right = max(cell[0] + cell[2] for cell in group_cells)
        bottom = max(cell[1] + cell[3] for cell in group_cells)
        confidence = float(np.mean(scores[group]))
        max_index = max(group, key=lambda index: scores[index])
        regions.append(SuspiciousRegion(
            x=x,
            y=y,
            width=right - x,
            height=bottom - y,
            confidence=round(confidence, 3),
            reason=_region_reason(
                float(noise_scores[max_index]),
                float(edge_scores[max_index]),
                float(compression_scores[max_index]),
            ),
        ))
    return sorted(regions, key=lambda region: region.confidence, reverse=True)[:5]


def analyze_image_forensics(investigation_id: str) -> ImageForensicsResponse:
    """Run dimension, grayscale, edge, local-noise, and recompression heuristics."""
    path = investigation_file(investigation_id)
    if path.suffix.lower() not in IMAGE_SUFFIXES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Image forensic analysis is supported only for PNG, JPG, and JPEG evidence.",
        )

    rgb = _load_image(path)
    height, width = rgb.shape[:2]
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    grayscale_stddev = float(gray.std())
    clipped_fraction = float(np.mean((gray <= 5) | (gray >= 250)))

    edges = cv2.Canny(gray, 80, 160)
    edge_density = float(np.mean(edges > 0))

    denoised = cv2.GaussianBlur(gray, (3, 3), 0)
    noise_residual = cv2.absdiff(gray, denoised).astype(np.float32)

    # Compare with a standard JPEG recompression.  This is an inspection signal,
    # not a statement about how the original file was created.
    encoded_ok, encoded = cv2.imencode(".jpg", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not encoded_ok:  # OpenCV's in-memory JPEG encoder should be available.
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Image recompression comparison failed.")
    recompressed = cv2.imdecode(encoded, cv2.IMREAD_GRAYSCALE)
    compression_difference = cv2.absdiff(gray, recompressed).astype(np.float32)

    tile_size = max(16, min(64, min(width, height) // 8 or 16))
    noise_values, cells = _tile_means(noise_residual, tile_size)
    edge_values, _ = _tile_means((edges > 0).astype(np.float32), tile_size)
    compression_values, _ = _tile_means(compression_difference, tile_size)
    noise_scores = _positive_outlier_scores(noise_values)
    edge_scores = _positive_outlier_scores(edge_values)
    compression_scores = _positive_outlier_scores(compression_values)
    local_scores = np.clip(0.45 * noise_scores + 0.25 * edge_scores + 0.30 * compression_scores, 0.0, 1.0)
    regions = _build_regions(
        cells, local_scores, noise_scores, edge_scores, compression_scores, tile_size, width, height
    )

    signals = [
        ImageForensicsSignal(
            kind="Image dimensions",
            message="Image dimensions were measured from the decoded evidence.",
            confidence=1.0,
            details={"width": width, "height": height},
        ),
        ImageForensicsSignal(
            kind="Grayscale analysis",
            message="Grayscale tonal distribution was measured for comparison across the image.",
            confidence=round(min(1.0, grayscale_stddev / 64), 3),
            details={"standard_deviation": round(grayscale_stddev, 3), "clipped_fraction": round(clipped_fraction, 4)},
        ),
        ImageForensicsSignal(
            kind="Edge analysis",
            message="Edge density was measured to identify abrupt local detail changes.",
            confidence=round(min(1.0, edge_density * 8), 3),
            details={"edge_density": round(edge_density, 4)},
        ),
        ImageForensicsSignal(
            kind="Local noise analysis",
            message="Local high-frequency variation was compared between image regions.",
            confidence=round(float(noise_scores.max(initial=0.0)), 3),
            details={"max_local_noise_score": round(float(noise_scores.max(initial=0.0)), 3)},
        ),
        ImageForensicsSignal(
            kind="Compression inconsistency",
            message="A JPEG recompression comparison found regions with varying reconstruction error; this is a heuristic, not proof of manipulation.",
            confidence=round(float(compression_scores.max(initial=0.0)), 3),
            details={"mean_recompression_difference": round(float(compression_difference.mean()), 3)},
        ),
    ]
    overall_score = float(local_scores.max(initial=0.0))
    return ImageForensicsResponse(
        signals=signals,
        suspicious_regions=regions,
        overall_anomaly_score=round(overall_score, 3),
    )
