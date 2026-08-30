import hashlib
import os
import re
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.models.investigation import InvestigationResponse


MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024
CHUNK_SIZE_BYTES = 1024 * 1024
ALLOWED_FILE_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".pdf": "application/pdf",
}
DEFAULT_EVIDENCE_DIR = Path(__file__).resolve().parents[2] / "data" / "evidence"


def evidence_directory() -> Path:
    """Return the configurable local directory used for uploaded evidence."""
    return Path(os.environ.get("PROOFMESH_EVIDENCE_DIR", DEFAULT_EVIDENCE_DIR))


def investigation_file(investigation_id: str) -> Path:
    """Find the single original evidence file for an investigation."""
    investigation_dir = evidence_directory() / investigation_id
    if not investigation_dir.is_dir():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation not found.")

    files = [path for path in investigation_dir.iterdir() if path.is_file() and not path.name.startswith(".")]
    if len(files) != 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file not found.")
    return files[0]


def _validate_upload(file: UploadFile) -> tuple[str, str]:
    original_name = file.filename or ""
    extension = Path(original_name).suffix.lower()
    expected_content_type = ALLOWED_FILE_TYPES.get(extension)
    if not original_name or not expected_content_type:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PNG, JPG, JPEG, and PDF files are supported.",
        )
    if file.content_type not in {expected_content_type, "application/octet-stream"}:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="The uploaded file type does not match its extension.",
        )
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", Path(original_name).name)
    return safe_name, expected_content_type


async def store_evidence(file: UploadFile) -> InvestigationResponse:
    """Validate, hash, and persist one evidence file without loading it all in memory."""
    safe_name, file_type = _validate_upload(file)
    investigation_id = str(uuid4())
    destination_dir = evidence_directory() / investigation_id
    destination_dir.mkdir(parents=True, exist_ok=False)
    temporary_path = destination_dir / f".{safe_name}.uploading"
    final_path = destination_dir / safe_name
    file_size = 0
    digest = hashlib.sha256()

    try:
        with temporary_path.open("wb") as destination:
            while chunk := await file.read(CHUNK_SIZE_BYTES):
                file_size += len(chunk)
                if file_size > MAX_FILE_SIZE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Files must not exceed 50 MB.",
                    )
                digest.update(chunk)
                destination.write(chunk)
        if file_size == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded file is empty.")

        temporary_path.replace(final_path)
        return InvestigationResponse(
            investigation_id=investigation_id,
            filename=file.filename or safe_name,
            file_type=file_type,
            file_size=file_size,
            sha256=digest.hexdigest(),
        )
    except Exception:
        temporary_path.unlink(missing_ok=True)
        if destination_dir.exists() and not any(destination_dir.iterdir()):
            destination_dir.rmdir()
        raise
    finally:
        await file.close()
