# ProofMesh

Minimal local foundation for the ProofMesh evidence-integrity MVP.

## Prerequisites

- Python 3.11+
- Node.js 20+

## Run the backend

From the project root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`. Verify it at:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

## Run the frontend

Open a second PowerShell window from the project root:

```powershell
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite (normally `http://localhost:5173`). The landing page calls the backend health endpoint automatically.

## Verify

```powershell
cd backend
pytest

cd ..\frontend
npm run build
```

If the backend runs on a different address, start Vite with its API URL:

```powershell
$env:VITE_API_URL = "http://127.0.0.1:8000"
npm run dev
```

## Image forensic limitations

`POST /api/v1/investigations/{id}/analyze/copy-move` uses a bounded ORB
feature-matching pass to highlight potentially repeated areas. It is an
investigative lead, not proof that an image was copied or manipulated.

It may report naturally repeated textures, patterns, or decorations. It can
miss small, smooth, blurred, heavily compressed, or strongly rotated/scaled
copied areas. Tiny, blank, and low-texture images return an empty region list
with an explanatory signal rather than an error.

## OCR requirements

The OCR endpoint needs both the Python package in `backend/requirements.txt`
and the native [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
executable available on the server `PATH`. Install the native executable using
your platform's package manager (for example, `brew install tesseract` on
macOS or `sudo apt install tesseract-ocr` on Debian/Ubuntu), then restart the
backend. If it is unavailable, the endpoint returns HTTP 200 with empty text
and blocks plus an `OCR unavailable` finding.

For image evidence, OCR boxes are source-image pixels. For PDFs, pages are
rendered at 2x scale, and box coordinates apply to that rendered page size.

## Document-layout analysis limitations

Document forensics compares OCR text geometry, spacing, alignment, duplicated
wording, density, and overlap with heuristic image regions. OCR itself can
misread text or positions, and intentional templates can have unusual layout.
These are review signals only. ProofMesh does not identify a font from this
pipeline and reports layout observations as `Text rendering/layout
inconsistency` instead.
