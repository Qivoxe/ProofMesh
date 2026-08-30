# ProofMesh

AI-powered digital evidence integrity platform. Upload PNG, JPG, or PDF evidence and receive a structured forensic investigation including metadata analysis, image forensics, OCR, document-layout analysis, an evidence integrity score, suspicious regions, and an evidence graph.

## Table of Contents

1. [Overview](#overview)
2. [Tech Stack](#tech-stack)
3. [Architecture](#architecture)
4. [Quick Start](#quick-start)
5. [Backend Setup](#backend-setup)
6. [Frontend Setup](#frontend-setup)
7. [API Reference](#api-reference)
8. [Analysis Pipeline](#analysis-pipeline)
9. [Frontend Screens](#frontend-screens)
10. [Testing](#testing)
11. [Build](#build)
12. [Environment Variables](#environment-variables)
13. [Known Limitations](#known-limitations)
14. [Hackathon Notes](#hackathon-notes)

## Overview

ProofMesh is a minimal local foundation for an evidence-integrity MVP. It stores uploaded evidence locally, computes a SHA-256 fingerprint, and runs multiple forensic analysis modules against the file. The frontend presents results through an investigation flow: upload → analyze → review.

**Core value proposition:** Securely preserve evidence locally, extract measurable forensic signals, and present them in an explainable investigation report — without claiming proof of manipulation.

## Tech Stack

### Backend
- **Runtime:** Python 3.11+
- **Framework:** FastAPI 0.115.6
- **Server:** Uvicorn 0.34.0
- **Image processing:** Pillow 12.3.0, OpenCV 4.10.0.84
- **PDF processing:** PyMuPDF 1.28.2
- **OCR:** pytesseract 0.3.13 + native Tesseract executable
- **Graph:** NetworkX 3.4.2
- **Testing:** pytest 8.3.4
- **HTTP client:** httpx 0.28.1

### Frontend
- **Runtime:** Node.js 20+
- **Framework:** React 19.0.0
- **Build tool:** Vite 6.0.5
- **Language:** TypeScript ~5.6.2
- **Styling:** Tailwind CSS 3.4.17
- **No additional UI libraries** — custom components only

## Architecture

```
ProofMesh/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app entry point
│   │   ├── api/
│   │   │   └── router.py           # All API endpoints
│   │   ├── models/
│   │   │   ├── health.py           # Health response model
│   │   │   └── investigation.py    # All analysis response models
│   │   ├── services/
│   │   │   ├── evidence_storage.py # Upload, hash, persist evidence
│   │   │   ├── metadata_analysis.py # EXIF / PDF metadata extraction
│   │   │   ├── image_forensics.py  # Lightweight image heuristics
│   │   │   ├── copy_move_detection.py # ORB-based copy-move detection
│   │   │   ├── ocr.py              # Tesseract OCR wrapper
│   │   │   ├── document_forensics.py # Layout analysis via OCR geometry
│   │   │   ├── evidence_fusion.py  # Integrity score calculation
│   │   │   └── evidence_graph.py   # NetworkX graph construction
│   │   ├── forensics/              # Reserved for future modules
│   │   ├── graph/                  # Reserved for future modules
│   │   ├── core/                   # Reserved for future config
│   │   └── reports/                # Reserved for future reporting
│   ├── tests/                      # 28 pytest tests
│   ├── data/evidence/              # Local evidence storage (gitignored)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── main.tsx                # React entry point
│   │   ├── App.tsx                 # Root component with state management
│   │   ├── pages/
│   │   │   ├── LandingPage.tsx     # Upload screen with health check
│   │   │   └── InvestigationResults.tsx # Results dashboard
│   │   ├── components/
│   │   │   ├── EvidenceUpload.tsx  # Drag-and-drop file upload
│   │   │   ├── HealthStatus.tsx    # API connection indicator
│   │   │   ├── AnalysisProgress.tsx # Step-by-step analysis progress
│   │   │   ├── EvidenceInfo.tsx    # File metadata display
│   │   │   ├── IntegrityScore.tsx  # Circular score gauge
│   │   │   ├── FindingsList.tsx    # Unified findings with severity
│   │   │   ├── ForensicSignals.tsx # Per-category signal cards
│   │   │   ├── ImageViewer.tsx     # Image with overlay toggles
│   │   │   ├── OCRPanel.tsx        # OCR text display
│   │   │   └── EvidenceGraph.tsx   # SVG force-directed graph
│   │   ├── services/
│   │   │   └── api.ts              # Typed API client (all endpoints)
│   │   ├── types/
│   │   │   ├── health.ts           # Health response types
│   │   │   ├── investigation.ts    # Investigation response types
│   │   │   ├── analysis.ts         # All analysis response types
│   │   │   └── graph.ts            # Evidence graph types
│   │   └── lib/
│   │       └── format.ts           # Byte formatting utility
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── tailwind.config.js
└── README.md
```

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- Git

### 1. Clone and enter
```powershell
git clone <repo-url>
cd ProofMesh
```

### 2. Start backend (PowerShell window 1)
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend runs at `http://127.0.0.1:8000`.

### 3. Start frontend (PowerShell window 2)
```powershell
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`.

### 4. Verify
- Open `http://localhost:5173` in a browser.
- Landing page shows health status (green dot = connected).
- Drag-and-drop or select a PNG/JPG/PDF to start an investigation.

## Backend Setup

### Virtual Environment
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Install Dependencies
```powershell
pip install -r requirements.txt
```

### Run Development Server
```powershell
uvicorn app.main:app --reload
```

The `--reload` flag auto-restarts on code changes.

### Health Check
```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Expected response:
```json
{"status": "ok", "service": "proofmesh"}
```

### Evidence Storage
Uploaded files are stored in `backend/data/evidence/{investigation-id}/`. This directory is gitignored. The path is configurable via the `PROOFMESH_EVIDENCE_DIR` environment variable.

## Frontend Setup

### Install Dependencies
```powershell
cd frontend
npm install
```

### Run Development Server
```powershell
npm run dev
```

Vite prints the local URL (normally `http://localhost:5173`).

### Custom API URL
If the backend runs on a different host/port, set `VITE_API_URL` before starting Vite:
```powershell
$env:VITE_API_URL = "http://127.0.0.1:8000"
npm run dev
```

## API Reference

All endpoints are prefixed with `/api/v1` where applicable. The base URL is configurable via `VITE_API_URL` on the frontend.

### Health
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service readiness check |

### Investigations
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/investigations` | Upload evidence file (multipart/form-data) |
| POST | `/api/v1/investigations/{id}/analyze/metadata` | Extract metadata |
| POST | `/api/v1/investigations/{id}/analyze/image` | Image forensics |
| POST | `/api/v1/investigations/{id}/analyze/copy-move` | Copy-move detection |
| POST | `/api/v1/investigations/{id}/analyze/ocr` | OCR text extraction |
| POST | `/api/v1/investigations/{id}/analyze/document` | Document forensics |
| POST | `/api/v1/investigations/{id}/analyze/fusion` | Evidence fusion / integrity score |
| GET | `/api/v1/investigations/{id}/graph` | Evidence graph |

### Upload Constraints
- Supported file types: `.png`, `.jpg`, `.jpeg`, `.pdf`
- Maximum file size: 50 MB
- Content-Type must match extension (or `application/octet-stream`)
- Returns: `investigation_id`, `filename`, `file_type`, `file_size`, `sha256`

## Analysis Pipeline

After a successful upload, the frontend automatically triggers all applicable analyses in sequence:

1. **Metadata Analysis** — Extracts EXIF data from images or PDF metadata. Flags editing software, timestamp inconsistencies, and missing metadata.
2. **Image Forensics** — Measures grayscale distribution, edge density, local noise tiles, JPEG recompression differences. Returns suspicious regions with confidence scores.
3. **Copy-Move Detection** — Uses ORB feature matching with RANSAC spatial consistency. Returns potential duplicated regions. Gracefully handles tiny, blank, or low-texture images.
4. **OCR** — Extracts text and word-level bounding boxes via Tesseract. Supports images and PDFs (rendered at 2x scale). Returns gracefully when Tesseract is unavailable.
5. **Document Forensics** — Analyzes OCR geometry for spacing, alignment, density, and isolated text. Detects duplicated wording. For images, relates OCR blocks to suspicious image regions.
6. **Evidence Fusion** — Combines all signals into a reproducible Evidence Integrity Score (0–100). Starts at 100 and deducts weighted concern points. Returns risk level, confidence, category concern scores, and normalized weights.
7. **Evidence Graph** — Builds a NetworkX graph linking artifacts, metadata, timestamps, signals, regions, OCR blocks, document findings, and fusion findings.

If any single analysis fails, the pipeline continues with the remaining analyses. Errors are displayed in the UI.

## Frontend Screens

### Landing Page
- Health status indicator (loading/online/offline)
- Brand header and value proposition
- Drag-and-drop or click-to-select file upload
- File validation (type, size)
- Upload progress and success confirmation with SHA-256

### Analysis Progress
- Step-by-step progress indicator
- Active step highlighted with spinner
- Completed steps marked with checkmark
- Steps: Uploading → Ingesting Evidence → Metadata → Image Forensics → Copy-Move → OCR → Document Analysis → Evidence Fusion → Evidence Graph

### Investigation Results
Organized into sections:

**Evidence Info**
- Filename, file type, size, SHA-256

**Integrity Score**
- Circular gauge showing 0–100 score
- Risk level badge (LOW / MODERATE / ELEVATED / HIGH)
- Confidence percentage
- Human-readable explanation

**Findings**
- Unified list from metadata, document, fusion, and OCR
- Severity-coded cards (high/medium/low/info)
- Confidence percentages

**Forensic Signals**
- Per-category summary cards: Metadata, Image Forensics, Copy-Move, OCR, Document
- Actual backend values (scores, counts, signal kinds)

**Image Evidence** (images only)
- Displays uploaded image
- Toggle suspicious-region overlays (rose boxes)
- Toggle OCR bounding-box overlays (cyan boxes)

**OCR**
- Extracted text with confidence summary
- Graceful "OCR unavailable" message when Tesseract is absent

**Evidence Graph**
- SVG force-directed visualization
- Color-coded node types
- Edges show relationships between artifacts, signals, regions, and findings

## Testing

### Backend Tests
28 pytest tests covering all analysis modules and the API layer.

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pytest --basetemp=C:\Users\Dell\OneDrive\Desktop\ProofMesh\backend\.pytest_tmp -q
```

**Note on Windows:** The default pytest temp directory may be inaccessible. Use `--basetemp` to specify a writable path.

### Frontend Build
```powershell
cd frontend
npm run build
```

This runs TypeScript type checking (`tsc -b`) followed by Vite production build.

## Build

### Frontend Production Build
```powershell
cd frontend
npm run build
```

Output: `frontend/dist/` (static files ready for deployment)

### Backend
No separate build step required. Dependencies are installed via `pip install -r requirements.txt`.

## Environment Variables

### Backend
| Variable | Description | Default |
|----------|-------------|---------|
| `PROOFMESH_EVIDENCE_DIR` | Directory for uploaded evidence storage | `backend/data/evidence` |
| `PROOFMESH_FUSION_METADATA_WEIGHT` | Metadata category weight | 0.15 |
| `PROOFMESH_FUSION_IMAGE_WEIGHT` | Image category weight | 0.30 |
| `PROOFMESH_FUSION_OCR_WEIGHT` | OCR category weight | 0.10 |
| `PROOFMESH_FUSION_DOCUMENT_WEIGHT` | Document category weight | 0.25 |
| `PROOFMESH_FUSION_CROSS_SIGNAL_WEIGHT` | Cross-signal category weight | 0.20 |

Weights are renormalized to sum to 1. Set to 0 to disable a category.

### Frontend
| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API base URL | `http://127.0.0.1:8000` |

Set before `npm run dev` if backend is not at the default address.

## Known Limitations

### OCR
- Requires native Tesseract executable on server `PATH`.
- Without Tesseract, the endpoint returns HTTP 200 with `OCR unavailable` finding.
- Install Tesseract via platform package manager and restart backend.

### Image Forensics
- Measures lightweight heuristics only; does not prove manipulation.
- May flag naturally repeated textures or patterns.
- Misses small, smooth, blurred, heavily compressed, or strongly transformed regions.
- Tiny, blank, or low-texture images return empty region lists with explanatory signals.

### Copy-Move Detection
- Uses bounded ORB feature matching; returns empty regions for insufficient texture.
- Naturally repeated patterns may produce false signals.
- Heuristic only — not proof of copying.

### Document Forensics
- Relies on OCR geometry; OCR misreads can propagate.
- Does not identify fonts; reports layout observations instead.
- Multi-page PDFs do not get OCR/image-region overlap analysis.

### Evidence Graph
- Uses a lightweight custom force simulation in the frontend.
- No React Flow or external graph library.

### CORS
- Backend allows `http://localhost:5173` and `http://127.0.0.1:5173` only.
- Other origins require CORS configuration update in `backend/app/main.py`.

### Windows Tests
- `pytest` requires `--basetemp` on this environment due to Temp folder permissions.
- Code is correct; issue is environment-specific.

## Hackathon Notes

### What Was Built
- Full-stack MVP with FastAPI backend and React 19 frontend.
- 9 backend endpoints, all functional and tested.
- 7 forensic analysis modules (metadata, image, copy-move, OCR, document, fusion, graph).
- 28 passing backend tests.
- Frontend with upload flow, analysis progress, results dashboard, image overlays, OCR panel, and evidence graph.
- Production build succeeds with zero TypeScript errors.

### What Was NOT Built (intentionally)
- No database (evidence stored locally in filesystem).
- No authentication or user accounts.
- No Docker or containerization.
- No ML models beyond heuristics.
- No external graph database.
- No report generation (placeholder exists in `backend/app/reports/__init__.py`).

### Demo Flow
1. Start backend and frontend.
2. Upload a PNG or JPG with interesting features.
3. Watch analysis progress steps.
4. Review integrity score, findings, signals.
5. Toggle image overlays to see suspicious regions and OCR boxes.
6. Explore evidence graph to understand signal relationships.

### Judging Highlights
- **Completeness:** All 9 backend endpoints functional. Frontend covers upload through results.
- **Correctness:** 28 tests pass. No mock data in production paths.
- **Explainability:** Every finding includes source, kind, message, and confidence. Score is reproducible with documented weights.
- **UX:** Clear progress states, graceful error handling, OCR unavailable fallback.
- **Code Quality:** Typed throughout (Python type hints + TypeScript). No `any` types. Clean separation of concerns.
