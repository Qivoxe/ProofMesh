# ProofMesh

**AI-powered evidence integrity analysis — upload, verify, explain.**

ProofMesh takes a piece of digital evidence (image or PDF) and runs it through a forensic pipeline that fuses metadata analysis, image forensics, copy-move detection, OCR, and document-layout analysis into a single, explainable **Evidence Integrity Score**. Every finding is traceable to its source signal — no black-box verdicts, no unsubstantiated claims of manipulation.

**[Live Demo](https://proof-mesh-ewoo6yjwc-shivamroy.vercel.app/)** · **[API Docs](https://proofmesh.onrender.com/docs)** · **[Backend](https://proofmesh.onrender.com)**

---

## Why ProofMesh

Digital evidence is everywhere — screenshots, scanned documents, photos — and almost none of it comes with a way to check its integrity. Existing tools either give a binary "fake/real" verdict with no reasoning, or require heavyweight forensic software. ProofMesh sits in between: a fast, explainable pipeline that surfaces *measurable* signals (EXIF inconsistencies, recompression artifacts, duplicated regions, layout anomalies) and lets the reviewer draw the conclusion.

## How It Works

```
Upload → SHA-256 fingerprint → Metadata → Image Forensics → Copy-Move → OCR → Document Forensics → Fusion → Evidence Graph
```

1. **Metadata Analysis** — EXIF/PDF metadata extraction; flags editing software, timestamp inconsistencies, missing fields.
2. **Image Forensics** — Grayscale distribution, edge density, noise-tile variance, JPEG recompression differentials; returns suspicious regions with confidence scores.
3. **Copy-Move Detection** — ORB feature matching + RANSAC spatial consistency to flag duplicated regions.
4. **OCR** — Tesseract-based text and word-bounding-box extraction (images + rendered PDFs), with graceful fallback if Tesseract is unavailable.
5. **Document Forensics** — Analyzes OCR geometry for spacing, alignment, density, and duplicated wording.
6. **Evidence Fusion** — Combines every signal into a reproducible 0–100 integrity score with documented, configurable category weights.
7. **Evidence Graph** — A NetworkX graph linking artifacts, signals, regions, and findings, rendered client-side as an SVG force layout.

If any single module fails, the pipeline degrades gracefully and continues — the UI surfaces the error rather than blocking the investigation.

## Tech Stack

| Layer | Stack |
|---|---|
| Backend | Python 3.11, FastAPI, Uvicorn, OpenCV, Pillow, PyMuPDF, Tesseract OCR, NetworkX |
| Frontend | React 19, Vite, TypeScript, Tailwind CSS |
| Testing | pytest (28 tests, backend fully covered) |

No auth, no database, no Docker — this is a scoped MVP that stores evidence locally and keeps the surface area small enough to fully test.

## Quick Start

**Backend**
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Runs at `http://127.0.0.1:8000`. Health check: `Invoke-RestMethod http://127.0.0.1:8000/health`

**Frontend**
```powershell
cd frontend
npm install
npm run dev
```
Runs at `http://localhost:5173`. Point it at a non-default backend with `$env:VITE_API_URL`.

## API Reference

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Service readiness check |
| POST | `/api/v1/investigations` | Upload evidence (multipart) |
| POST | `/api/v1/investigations/{id}/analyze/metadata` | Metadata extraction |
| POST | `/api/v1/investigations/{id}/analyze/image` | Image forensics |
| POST | `/api/v1/investigations/{id}/analyze/copy-move` | Copy-move detection |
| POST | `/api/v1/investigations/{id}/analyze/ocr` | OCR extraction |
| POST | `/api/v1/investigations/{id}/analyze/document` | Document forensics |
| POST | `/api/v1/investigations/{id}/analyze/fusion` | Integrity score |
| GET | `/api/v1/investigations/{id}/graph` | Evidence graph |

Upload constraints: `.png`, `.jpg`, `.jpeg`, `.pdf`, max 50 MB.

## Project Structure

```
ProofMesh/
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI routes
│   │   ├── models/         # Pydantic response models
│   │   ├── services/       # Analysis modules (one per pipeline stage)
│   │   └── graph/          # Evidence graph construction
│   └── tests/               # 28 pytest tests
└── frontend/
    └── src/
        ├── pages/           # Landing + investigation results
        ├── components/      # Upload, progress, findings, graph, overlays
        └── services/        # Typed API client
```

## What's Explainable, Not Absolute

Every module is a heuristic, not a verdict:
- **Image forensics** flags anomalies but can miss subtle or heavily-compressed edits, and can false-positive on naturally repeated textures.
- **Copy-move detection** needs sufficient texture to work and is not proof of duplication.
- **Document forensics** inherits any OCR misreads and doesn't identify fonts — it reports layout, not authorship.

This is intentional: ProofMesh is built to *surface signals for human review*, not to replace forensic judgment.

## What We'd Build Next

- Persistent storage + auth for multi-case workflows
- ML-based manipulation detection beyond heuristic signals
- PDF-level OCR/image-region overlap for multi-page documents
- Exportable investigation reports (PDF/JSON)

## Team

Shivam · Nancy · Gopal Kumar
