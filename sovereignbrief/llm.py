"""OpenAI-compatible HTTP client for Apertus (HF Inference Providers or local)."""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

from sovereignbrief.config import Settings
from sovereignbrief.schema import BRIEFING_JSON_SCHEMA_HINT, Briefing, NextAction


SYSTEM_PROMPT = """You are SovereignBrief, an ops briefing assistant powered by Apertus.
Read the user's document and return ONLY a single JSON object matching this schema
(no markdown fences, no commentary before or after the JSON):

""" + BRIEFING_JSON_SCHEMA_HINT + """

Rules:
- next_actions MUST contain exactly 5 items when the source allows; if thin, still return 5 best-effort steps.
- Be concrete and actionable; do not invent facts not supported by the text.
- If second_language_target is provided in the user message, fill second_language with a concise brief in that language and set second_language_code accordingly; otherwise set both to null.
- risks and decisions_needed should be short bullet-ready strings.
"""


def build_user_prompt(
    document_text: str,
    second_language: str | None = None,
) -> str:
    lang_line = (
        f"second_language_target: {second_language}"
        if second_language
        else "second_language_target: none"
    )
    return (
        f"{lang_line}\n\n"
        "--- DOCUMENT START ---\n"
        f"{document_text.strip()}\n"
        "--- DOCUMENT END ---\n\n"
        "Respond with JSON only."
    )


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError("Model response did not contain a JSON object")
    data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("Model JSON was not an object")
    return data


def _coerce_briefing(data: dict[str, Any]) -> Briefing:
    actions_raw = data.get("next_actions") or []
    actions: list[NextAction] = []
    for item in actions_raw[:5]:
        if isinstance(item, str):
            actions.append(NextAction(action=item))
        elif isinstance(item, dict):
            actions.append(
                NextAction(
                    action=str(item.get("action") or item.get("step") or "Review"),
                    owner=str(item.get("owner") or "Unassigned"),
                    due=str(item.get("due") or "TBD"),
                )
            )
    while len(actions) < 5:
        actions.append(
            NextAction(
                action="Clarify remaining unknowns with the document owner",
                owner="Unassigned",
                due="TBD",
            )
        )
    return Briefing(
        summary=str(data.get("summary") or "No summary produced."),
        risks=[str(r) for r in (data.get("risks") or [])],
        decisions_needed=[str(d) for d in (data.get("decisions_needed") or [])],
        next_actions=actions[:5],
        open_questions=[str(q) for q in (data.get("open_questions") or [])],
        second_language=(
            str(data["second_language"])
            if data.get("second_language") not in (None, "", "null")
            else None
        ),
        second_language_code=(
            str(data["second_language_code"])
            if data.get("second_language_code") not in (None, "", "null")
            else None
        ),
    )


def _redact_secrets(text: str) -> str:
    """Strip tokens and Authorization headers before errors leave this module."""
    text = re.sub(r"(?i)bearer\s+\S+", "Bearer REDACTED", text)
    text = re.sub(r"hf_[A-Za-z0-9_\-]+", "hf_REDACTED", text)
    return text


def _model_missing(status_code: int, body_text: str) -> bool:
    """True when the router does not serve this model id (safe to try fallback)."""
    if status_code == 404:
        return True
    lowered = body_text.lower()
    if status_code == 400 and (
        "not found" in lowered
        or "does not exist" in lowered
        or "no provider" in lowered
        or "model" in lowered and "not supported" in lowered
        or "unknown model" in lowered
    ):
        return True
    return False


def _models_to_try(settings: Settings) -> list[str]:
    models = [settings.apertus_model]
    fallback = settings.apertus_fallback_model
    if (
        fallback
        and fallback not in models
        and not settings.is_local_endpoint
    ):
        models.append(fallback)
    return models


async def call_apertus(
    settings: Settings,
    document_text: str,
    second_language: str | None = None,
    client: httpx.AsyncClient | None = None,
    max_tokens: int = 2048,
) -> Briefing:
    token = settings.require_token_for_remote()
    url = f"{settings.apertus_base_url}/chat/completions"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": build_user_prompt(document_text, second_language),
        },
    ]

    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(timeout=settings.apertus_timeout)
    assert client is not None
    try:
        models = _models_to_try(settings)
        response: httpx.Response | None = None
        for index, model in enumerate(models):
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": max_tokens,
            }
            response = await client.post(url, headers=headers, json=payload)
            body_text = response.text or ""
            has_next = index < len(models) - 1
            if has_next and _model_missing(response.status_code, body_text):
                continue
            break
    finally:
        if owns_client:
            await client.aclose()

    assert response is not None
    if response.status_code == 401:
        raise RuntimeError(
            "Apertus endpoint returned 401 Unauthorized. "
            "Check HF_TOKEN permissions (Inference Providers) or local auth."
        )
    if response.status_code == 402:
        raise RuntimeError(
            "Apertus HTTP 402: included Hugging Face credits are exhausted "
            "or this route requires a paid balance. Not purchasing credits."
        )
    if response.status_code >= 400:
        safe = _redact_secrets(response.text[:500])
        raise RuntimeError(f"Apertus HTTP {response.status_code}: {safe}")

    body = response.json()
    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("Unexpected chat completion shape") from exc

    if not isinstance(content, str):
        # Multimodal / list content — join text parts if present
        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    parts.append(str(part.get("text", "")))
                elif isinstance(part, str):
                    parts.append(part)
            content = "\n".join(parts)
        else:
            content = str(content)

    return _coerce_briefing(_extract_json_object(content))
