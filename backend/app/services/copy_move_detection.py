"""A bounded, explainable copy-move inspection heuristic based on ORB features.

This detects repeated visual features within one image and is deliberately not a
claim that copying occurred.  Repeated natural patterns and decorations can
produce matches; smooth, tiny, blurred, or heavily transformed copied content
may produce no match at all.
"""

from __future__ import annotations

from collections.abc import Iterable

import cv2
import numpy as np
from fastapi import HTTPException, status

from app.models.investigation import CopyMoveAnalysisResponse, ImageForensicsSignal, SuspiciousRegion
from app.services.evidence_storage import investigation_file
from app.services.image_forensics import IMAGE_SUFFIXES, _load_image


MIN_IMAGE_SIDE = 48
MIN_KEYPOINTS = 12
MIN_MATCHES = 8
MAX_FEATURES = 600
MIN_SEPARATION_PIXELS = 16
MAX_HAMMING_DISTANCE = 40


def _no_regions(kind: str, message: str, details: dict[str, int | float] | None = None) -> CopyMoveAnalysisResponse:
    return CopyMoveAnalysisResponse(
        signals=[ImageForensicsSignal(kind=kind, message=message, confidence=0.0, details=details or {})],
        suspicious_regions=[],
    )


def _filter_matches(keypoints: list[cv2.KeyPoint], descriptors: np.ndarray) -> list[cv2.DMatch]:
    """Keep only close, non-self, spatially separated descriptor matches."""
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    possible = matcher.knnMatch(descriptors, descriptors, k=min(4, len(descriptors)))
    selected: dict[tuple[int, int], cv2.DMatch] = {}
    for candidates in possible:
        non_self = [match for match in candidates if match.queryIdx != match.trainIdx]
        if not non_self:
            continue
        first = non_self[0]
        if first.distance > MAX_HAMMING_DISTANCE:
            continue
        if len(non_self) > 1 and first.distance >= 0.82 * non_self[1].distance:
            continue
        source = np.asarray(keypoints[first.queryIdx].pt)
        destination = np.asarray(keypoints[first.trainIdx].pt)
        if float(np.linalg.norm(source - destination)) < MIN_SEPARATION_PIXELS:
            continue
        pair = tuple(sorted((first.queryIdx, first.trainIdx)))
        old = selected.get(pair)
        if old is None or first.distance < old.distance:
            selected[pair] = first
    return list(selected.values())


def _region_from_points(points: np.ndarray, image_width: int, image_height: int, confidence: float) -> SuspiciousRegion:
    x, y, width, height = cv2.boundingRect(points.astype(np.float32))
    padding = 8
    left = max(0, x - padding)
    top = max(0, y - padding)
    right = min(image_width, x + width + padding)
    bottom = min(image_height, y + height + padding)
    return SuspiciousRegion(
        x=int(left),
        y=int(top),
        width=max(1, int(right - left)),
        height=max(1, int(bottom - top)),
        confidence=round(float(np.clip(confidence, 0.0, 1.0)), 3),
        reason="Potential copy-move region: spatially consistent repeated image features.",
    )


def _overlaps(a: SuspiciousRegion, b: SuspiciousRegion) -> bool:
    return a.x < b.x + b.width and b.x < a.x + a.width and a.y < b.y + b.height and b.y < a.y + a.height


def _unique_regions(regions: Iterable[SuspiciousRegion]) -> list[SuspiciousRegion]:
    result: list[SuspiciousRegion] = []
    for region in regions:
        if not any(_overlaps(region, existing) for existing in result):
            result.append(region)
    return result


def analyze_copy_move(investigation_id: str) -> CopyMoveAnalysisResponse:
    """Detect spatially consistent, repeated ORB features in an uploaded image."""
    path = investigation_file(investigation_id)
    if path.suffix.lower() not in IMAGE_SUFFIXES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Copy-move analysis is supported only for PNG, JPG, and JPEG evidence.",
        )

    rgb = _load_image(path)
    height, width = rgb.shape[:2]
    if min(width, height) < MIN_IMAGE_SIDE:
        return _no_regions(
            "Copy-move analysis unavailable",
            "The image is too small for reliable local-feature matching.",
            {"width": width, "height": height},
        )

    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    intensity_stddev = float(gray.std())
    if intensity_stddev < 2.0:
        return _no_regions(
            "Copy-move analysis unavailable",
            "The image is blank or near-uniform, so it has no reliable visual features to compare.",
            {"grayscale_standard_deviation": round(intensity_stddev, 3)},
        )

    detector = cv2.ORB_create(nfeatures=MAX_FEATURES, fastThreshold=12)
    keypoints, descriptors = detector.detectAndCompute(gray, None)
    if descriptors is None or len(keypoints) < MIN_KEYPOINTS:
        return _no_regions(
            "Copy-move analysis unavailable",
            "The image has too little texture for reliable local-feature matching.",
            {"keypoint_count": len(keypoints)},
        )

    matches = _filter_matches(keypoints, descriptors)
    if len(matches) < MIN_MATCHES:
        return _no_regions(
            "No spatially consistent copy-move signal",
            "No sufficient set of strong, separated repeated features was found. This does not rule out editing.",
            {"keypoint_count": len(keypoints), "strong_match_count": len(matches)},
        )

    source_points = np.float32([keypoints[match.queryIdx].pt for match in matches])
    destination_points = np.float32([keypoints[match.trainIdx].pt for match in matches])
    _, inlier_mask = cv2.estimateAffinePartial2D(
        source_points,
        destination_points,
        method=cv2.RANSAC,
        ransacReprojThreshold=4.0,
        maxIters=750,
        confidence=0.99,
        refineIters=5,
    )
    if inlier_mask is None:
        return _no_regions(
            "No spatially consistent copy-move signal",
            "Repeated features were found, but they did not form a consistent spatial relationship.",
            {"strong_match_count": len(matches)},
        )

    inliers = inlier_mask.ravel().astype(bool)
    inlier_count = int(inliers.sum())
    if inlier_count < MIN_MATCHES:
        return _no_regions(
            "No spatially consistent copy-move signal",
            "Repeated features did not meet the minimum spatial-consistency threshold.",
            {"strong_match_count": len(matches), "inlier_count": inlier_count},
        )

    inlier_ratio = inlier_count / len(matches)
    confidence = min(0.95, 0.35 + 0.04 * inlier_count + 0.25 * inlier_ratio)
    regions = _unique_regions([
        _region_from_points(source_points[inliers], width, height, confidence),
        _region_from_points(destination_points[inliers], width, height, confidence),
    ])
    return CopyMoveAnalysisResponse(
        signals=[ImageForensicsSignal(
            kind="Spatially consistent repeated features",
            message="ORB feature matches formed a repeated spatial pattern. This is a review signal, not proof of copying or manipulation.",
            confidence=round(confidence, 3),
            details={
                "keypoint_count": len(keypoints),
                "strong_match_count": len(matches),
                "spatially_consistent_match_count": inlier_count,
            },
        )],
        suspicious_regions=regions,
    )
