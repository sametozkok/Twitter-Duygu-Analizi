from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from backend.api.routes.health import router as health_router
from backend.api.routes.analyze import router as analyze_router

app = FastAPI(title="Twitter Analysis API", version="0.1.0")


def _parse_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "").strip()
    if raw:
        return [item.strip() for item in raw.split(",") if item.strip()]

    return [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


cors_origins = _parse_cors_origins()
cors_origin_regex = os.getenv("CORS_ORIGIN_REGEX")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=cors_origin_regex,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(analyze_router, prefix="/api")


@app.get("/")
def root() -> dict:
    return {"service": "twitter-analysis-api", "status": "ok"}
