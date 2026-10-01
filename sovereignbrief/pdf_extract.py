"""Small PDF text extraction via pypdf (server-side, free/local)."""

from __future__ import annotations

import io

from pypdf import PdfReader


MAX_PDF_BYTES = 2 * 1024 * 1024  # 2 MiB soft cap for MVP demos
MAX_CHARS = 40_000


def extract_text_from_pdf(data: bytes) -> str:
    if len(data) > MAX_PDF_BYTES:
        raise ValueError(
            f"PDF too large ({len(data)} bytes). MVP limit is {MAX_PDF_BYTES} bytes."
        )
    reader = PdfReader(io.BytesIO(data))
    chunks: list[str] = []
    for page in reader.pages:
        chunks.append(page.extract_text() or "")
    text = "\n".join(chunks).strip()
    if not text:
        raise ValueError("No extractable text found in PDF (scanned images not supported).")
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n\n[truncated]"
    return text
