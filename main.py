"""SovereignBrief FastAPI entrypoint — Hack Apertus Track 2B Own Project."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from sovereignbrief.config import load_settings
from sovereignbrief.llm import call_apertus
from sovereignbrief.pdf_extract import extract_text_from_pdf
from sovereignbrief.schema import Briefing

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
SAMPLES_DIR = APP_DIR / "samples"

# Load .env if present (no python-dotenv dep — minimal parser)
_env_path = APP_DIR / ".env"
if _env_path.is_file():
    for line in _env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)

app = FastAPI(
    title="SovereignBrief",
    description="Apertus-powered multilingual action briefs (Hack Apertus Track 2B).",
    version="0.1.0",
)

if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class BriefRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Document text to brief")
    second_language: Optional[str] = Field(
        default=None,
        description="Optional second language code: hi, en, or de",
    )


class HealthResponse(BaseModel):
    ok: bool
    model: str
    base_url: str
    token_configured: bool
    local_endpoint: bool


@app.get("/")
async def index() -> FileResponse:
    index_path = STATIC_DIR / "index.html"
    if not index_path.is_file():
        raise HTTPException(status_code=404, detail="static/index.html missing")
    return FileResponse(index_path)


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = load_settings()
    return HealthResponse(
        ok=True,
        model=settings.apertus_model,
        base_url=settings.apertus_base_url,
        token_configured=bool(settings.hf_token),
        local_endpoint=settings.is_local_endpoint,
    )


@app.get("/api/sample")
async def sample_text() -> dict:
    sample = SAMPLES_DIR / "sample_policy.txt"
    if not sample.is_file():
        raise HTTPException(status_code=404, detail="sample fixture missing")
    return {"filename": sample.name, "text": sample.read_text(encoding="utf-8")}


@app.post("/api/brief", response_model=Briefing)
async def brief_json(body: BriefRequest) -> Briefing:
    settings = load_settings()
    try:
        settings.require_token_for_remote()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    text = body.text.strip()
    if len(text) > 40_000:
        text = text[:40_000] + "\n\n[truncated]"

    lang = (body.second_language or "").strip().lower() or None
    if lang and lang not in {"hi", "en", "de"}:
        raise HTTPException(
            status_code=400,
            detail="second_language must be one of: hi, en, de",
        )

    try:
        return await call_apertus(settings, text, second_language=lang)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/brief/upload", response_model=Briefing)
async def brief_upload(
    text: Optional[str] = Form(default=None),
    second_language: Optional[str] = Form(default=None),
    file: Optional[UploadFile] = File(default=None),
) -> Briefing:
    settings = load_settings()
    try:
        settings.require_token_for_remote()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    document = (text or "").strip()
    if file is not None and file.filename:
        raw = await file.read()
        name = (file.filename or "").lower()
        if name.endswith(".pdf"):
            try:
                document = extract_text_from_pdf(raw)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        elif name.endswith(".txt") or name.endswith(".md"):
            document = raw.decode("utf-8", errors="replace").strip()
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Use .txt, .md, or small .pdf",
            )

    if not document:
        raise HTTPException(status_code=400, detail="Provide text or a supported file")

    if len(document) > 40_000:
        document = document[:40_000] + "\n\n[truncated]"

    lang = (second_language or "").strip().lower() or None
    if lang and lang not in {"hi", "en", "de"}:
        raise HTTPException(
            status_code=400,
            detail="second_language must be one of: hi, en, de",
        )

    try:
        return await call_apertus(settings, document, second_language=lang)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
