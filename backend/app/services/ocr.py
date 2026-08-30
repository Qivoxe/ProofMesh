"""OCR for uploaded image and PDF evidence, with a non-failing Tesseract fallback."""

from __future__ import annotations

from collections.abc import Iterable

import fitz
from fastapi import HTTPException, status
from PIL import Image, ImageOps, UnidentifiedImageError

try:
    import pytesseract
except ImportError:  # Allows the API to start if optional OCR dependencies were not installed.
    pytesseract = None

from app.models.investigation import OCRAnalysisResponse, OCRBlock, OCRFinding
from app.services.evidence_storage import investigation_file


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}
PDF_RENDER_SCALE = 2


def _unavailable_response() -> OCRAnalysisResponse:
    return OCRAnalysisResponse(findings=[OCRFinding(
        kind="OCR unavailable",
        message="Tesseract OCR is not installed or is not available on the server PATH. Install Tesseract and retry.",
    )])


def _parse_confidence(value: object) -> float | None:
    try:
        confidence = float(str(value))
    except (TypeError, ValueError):
        return None
    return confidence if confidence >= 0 else None


def _read_blocks(image: Image.Image, page: int) -> list[OCRBlock]:
    """Request Tesseract's word data, preserving coordinates for UI overlays."""
    assert pytesseract is not None
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    blocks: list[OCRBlock] = []
    for index, raw_text in enumerate(data.get("text", [])):
        text = str(raw_text).strip()
        confidence = _parse_confidence(data.get("conf", [None])[index])
        if not text or confidence is None:
            continue
        width = int(data.get("width", [0])[index])
        height = int(data.get("height", [0])[index])
        if width <= 0 or height <= 0:
            continue
        blocks.append(OCRBlock(
            text=text,
            confidence=round(min(100, confidence), 2),
            x=max(0, int(data.get("left", [0])[index])),
            y=max(0, int(data.get("top", [0])[index])),
            width=width,
            height=height,
            page=page,
        ))
    return blocks


def _response(blocks: Iterable[OCRBlock], findings: list[OCRFinding] | None = None) -> OCRAnalysisResponse:
    result_blocks = list(blocks)
    average = sum(block.confidence for block in result_blocks) / len(result_blocks) if result_blocks else 0
    pages: dict[int, list[str]] = {}
    for block in result_blocks:
        pages.setdefault(block.page, []).append(block.text)
    text = "\n\n".join(" ".join(page_text) for _, page_text in sorted(pages.items()))
    return OCRAnalysisResponse(
        text=text,
        blocks=result_blocks,
        average_confidence=round(average, 2),
        findings=findings or [],
    )


def _ocr_image(path: str) -> OCRAnalysisResponse:
    try:
        with Image.open(path) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            return _response(_read_blocks(image, page=1), [OCRFinding(
                kind="OCR coordinates",
                message="Bounding boxes use decoded source-image pixels and can be overlaid directly on the image.",
            )])
    except (UnidentifiedImageError, OSError) as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Image evidence could not be read for OCR.") from error


def _ocr_pdf(path: str) -> OCRAnalysisResponse:
    blocks: list[OCRBlock] = []
    try:
        with fitz.open(path) as document:
            for page_index, page in enumerate(document, start=1):
                pixmap = page.get_pixmap(matrix=fitz.Matrix(PDF_RENDER_SCALE, PDF_RENDER_SCALE), alpha=False)
                image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
                blocks.extend(_read_blocks(image, page=page_index))
    except (fitz.FileDataError, RuntimeError) as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="PDF evidence could not be rendered for OCR.") from error
    return _response(blocks, [OCRFinding(
        kind="OCR coordinates",
        message=f"PDF bounding boxes use pixels from pages rendered at {PDF_RENDER_SCALE}x scale; overlay them on the same rendered page size.",
    )])


def analyze_ocr(investigation_id: str) -> OCRAnalysisResponse:
    """Extract text, word boxes, and confidences without failing when Tesseract is absent."""
    path = investigation_file(investigation_id)
    if path.suffix.lower() not in IMAGE_SUFFIXES | {".pdf"}:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="OCR is supported only for PNG, JPG, JPEG, and PDF evidence.")
    if pytesseract is None:
        return _unavailable_response()
    try:
        pytesseract.get_tesseract_version()
    except (pytesseract.TesseractNotFoundError, OSError):
        return _unavailable_response()
    except pytesseract.TesseractError:
        return OCRAnalysisResponse(findings=[OCRFinding(
            kind="OCR unavailable",
            message="Tesseract could not be initialized for OCR. Check its language data and server configuration.",
        )])

    try:
        return _ocr_pdf(str(path)) if path.suffix.lower() == ".pdf" else _ocr_image(str(path))
    except pytesseract.TesseractNotFoundError:
        return _unavailable_response()
    except pytesseract.TesseractError:
        return OCRAnalysisResponse(findings=[OCRFinding(
            kind="OCR failed",
            message="Tesseract could not process this evidence. No OCR text or boxes were returned.",
        )])
