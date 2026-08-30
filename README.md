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
