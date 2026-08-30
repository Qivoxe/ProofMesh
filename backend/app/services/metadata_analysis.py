import re
from datetime import datetime
from pathlib import Path
from typing import Any

import fitz
from fastapi import HTTPException, status
from PIL import ExifTags, Image, UnidentifiedImageError

from app.models.investigation import MetadataAnalysisResponse, MetadataFinding
from app.services.evidence_storage import investigation_file


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}
EDITING_SOFTWARE_MARKERS = ("adobe", "photoshop", "lightroom", "gimp", "affinity", "canva", "pixelmator")


def _json_value(value: Any) -> str | int | float | bool | None:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _parse_exif_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value[:19], "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None


def _analyze_image(path: Path, investigation_id: str) -> MetadataAnalysisResponse:
    try:
        with Image.open(path) as image:
            exif = image.getexif()
            exif_data = {ExifTags.TAGS.get(tag, str(tag)): _json_value(value) for tag, value in exif.items()}
            timestamps = {
                key: exif_data[key]
                for key in ("DateTime", "DateTimeOriginal", "DateTimeDigitized")
                if exif_data.get(key)
            }
            camera = {key.lower(): exif_data.get(key) for key in ("Make", "Model") if exif_data.get(key)}
            software = exif_data.get("Software")
            metadata = {
                "dimensions": {"width": image.width, "height": image.height},
                "format": image.format,
                "exif": exif_data,
                "software": software,
                "timestamps": timestamps,
                "camera": camera,
            }
    except (UnidentifiedImageError, OSError) as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Image metadata could not be read.") from error

    findings: list[MetadataFinding] = []
    if not exif_data:
        findings.append(MetadataFinding(kind="Metadata unavailable", message="No embedded EXIF metadata was found. This alone does not indicate manipulation."))
    if software and any(marker in str(software).lower() for marker in EDITING_SOFTWARE_MARKERS):
        findings.append(MetadataFinding(kind="Editing software detected", message=f"The image Software metadata reports: {software}."))

    original = _parse_exif_timestamp(timestamps.get("DateTimeOriginal"))
    digitized = _parse_exif_timestamp(timestamps.get("DateTimeDigitized"))
    if original and digitized and original > digitized:
        findings.append(MetadataFinding(
            kind="Metadata timestamp inconsistency",
            message="DateTimeOriginal is later than DateTimeDigitized.",
            heuristic=True,
        ))

    return MetadataAnalysisResponse(
        investigation_id=investigation_id,
        file_type="image/png" if path.suffix.lower() == ".png" else "image/jpeg",
        metadata=metadata,
        findings=findings,
    )


def _parse_pdf_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    match = re.search(r"(\d{14})", value)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y%m%d%H%M%S")
    except ValueError:
        return None


def _analyze_pdf(path: Path, investigation_id: str) -> MetadataAnalysisResponse:
    try:
        with fitz.open(path) as document:
            document_metadata = {key: value for key, value in document.metadata.items() if value}
            metadata = {
                "page_count": document.page_count,
                "metadata": document_metadata,
                "author": document_metadata.get("author"),
                "creator": document_metadata.get("creator"),
                "producer": document_metadata.get("producer"),
                "creation_date": document_metadata.get("creationDate"),
                "modification_date": document_metadata.get("modDate"),
            }
    except (fitz.FileDataError, RuntimeError) as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="PDF metadata could not be read.") from error

    findings: list[MetadataFinding] = []
    if not any(metadata[key] for key in ("author", "creator", "producer", "creation_date", "modification_date")):
        findings.append(MetadataFinding(kind="Metadata unavailable", message="No document authoring metadata was found. This alone does not indicate manipulation."))

    created = _parse_pdf_timestamp(metadata["creation_date"])
    modified = _parse_pdf_timestamp(metadata["modification_date"])
    if created and modified and modified < created:
        findings.append(MetadataFinding(
            kind="Metadata timestamp inconsistency",
            message="The PDF modification date is earlier than its creation date.",
            heuristic=True,
        ))

    return MetadataAnalysisResponse(
        investigation_id=investigation_id,
        file_type="application/pdf",
        metadata=metadata,
        findings=findings,
    )


def analyze_metadata(investigation_id: str) -> MetadataAnalysisResponse:
    """Extract available embedded metadata and flag only observed metadata anomalies."""
    path = investigation_file(investigation_id)
    if path.suffix.lower() in IMAGE_SUFFIXES:
        return _analyze_image(path, investigation_id)
    if path.suffix.lower() == ".pdf":
        return _analyze_pdf(path, investigation_id)
    raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Metadata analysis is not supported for this file.")
