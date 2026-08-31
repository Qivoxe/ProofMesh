from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router


app = FastAPI(
    title="ProofMesh API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://proof-mesh-ewoo6yjwc-shivamroy.vercel.app",
        "https://proof-mesh-5qo1b58pg-shivamroy.vercel.app",
        "https://proof-mesh-kohl.vercel.app",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)