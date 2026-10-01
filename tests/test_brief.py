"""Minimal tests — mock the LLM HTTP call; no real HF_TOKEN required."""

from __future__ import annotations

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from sovereignbrief.config import Settings, load_settings
from sovereignbrief.llm import call_apertus, _coerce_briefing, _extract_json_object
from sovereignbrief.schema import Briefing


FAKE_BRIEF = {
    "summary": "Vendor access and retention rules need owners before 1 Nov.",
    "risks": ["US-region ticket storage", "Personal OCR accounts"],
    "decisions_needed": ["Approve Nov 1 date", "Accept HelpdeskPro pause"],
    "next_actions": [
        {"action": "Pin FormFlow to EU", "owner": "IT", "due": "1 week"},
        {"action": "Pause HelpdeskPro attachments", "owner": "Ops", "due": "Friday"},
        {"action": "Inventory CloudOCR accounts", "owner": "Security", "due": "2 weeks"},
        {"action": "Schedule retention batch", "owner": "IT", "due": "3 weeks"},
        {"action": "Nominate Hindi notice QA", "owner": "Clerk", "due": "Friday"},
    ],
    "open_questions": ["HelpdeskPro migrate budget?"],
    "second_language": "सारांश: विक्रेता पहुँच और प्रतिधारण नियमों को मालिक चाहिए।",
    "second_language_code": "hi",
}


def test_extract_json_from_fenced_response():
    raw = "```json\n" + json.dumps(FAKE_BRIEF) + "\n```"
    data = _extract_json_object(raw)
    assert data["summary"].startswith("Vendor")


def test_coerce_pads_to_five_actions():
    brief = _coerce_briefing(
        {
            "summary": "Thin note",
            "risks": [],
            "decisions_needed": [],
            "next_actions": [{"action": "Only one"}],
            "open_questions": [],
        }
    )
    assert isinstance(brief, Briefing)
    assert len(brief.next_actions) == 5


@pytest.mark.asyncio
async def test_call_apertus_mocked():
    settings = Settings(
        hf_token="hf_test_token",
        apertus_base_url="https://router.huggingface.co/v1",
        apertus_model="swiss-ai/Apertus-v1.5-8B",
        apertus_timeout=10.0,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/chat/completions")
        assert request.headers.get("Authorization") == "Bearer hf_test_token"
        body = {
            "choices": [
                {"message": {"role": "assistant", "content": json.dumps(FAKE_BRIEF)}}
            ]
        }
        return httpx.Response(200, json=body)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        brief = await call_apertus(
            settings,
            "sample document text",
            second_language="hi",
            client=client,
        )
    assert brief.summary.startswith("Vendor")
    assert len(brief.next_actions) == 5
    assert brief.second_language_code == "hi"


def test_missing_token_fails_clearly(monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("APERTUS_API_KEY", raising=False)
    monkeypatch.setenv("APERTUS_BASE_URL", "https://router.huggingface.co/v1")
    settings = load_settings()
    with pytest.raises(RuntimeError, match="HF_TOKEN is required"):
        settings.require_token_for_remote()


def test_local_endpoint_allows_missing_token(monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("APERTUS_API_KEY", raising=False)
    monkeypatch.setenv("APERTUS_BASE_URL", "http://127.0.0.1:8000/v1")
    settings = load_settings()
    assert settings.require_token_for_remote() is None


def test_api_brief_uses_mock(monkeypatch):
    async def fake_call(settings, document_text, second_language=None, client=None):
        return _coerce_briefing(FAKE_BRIEF)

    monkeypatch.setenv("HF_TOKEN", "hf_test_token")
    monkeypatch.setattr("main.call_apertus", fake_call)

    from main import app

    client = TestClient(app)
    r = client.post(
        "/api/brief",
        json={"text": "hello policy", "second_language": "hi"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["summary"].startswith("Vendor")
    assert len(data["next_actions"]) == 5


def test_api_health_and_sample(monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    from main import app

    client = TestClient(app)
    h = client.get("/api/health")
    assert h.status_code == 200
    assert h.json()["model"] == "swiss-ai/Apertus-v1.5-8B"
    s = client.get("/api/sample")
    assert s.status_code == 200
    assert "HelpdeskPro" in s.json()["text"]


def test_api_brief_503_without_token(monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("APERTUS_API_KEY", raising=False)
    monkeypatch.setenv("APERTUS_BASE_URL", "https://router.huggingface.co/v1")
    # Re-import not needed — load_settings reads env each call
    from main import app

    client = TestClient(app)
    r = client.post("/api/brief", json={"text": "x" * 20})
    assert r.status_code == 503
    assert "HF_TOKEN" in r.json()["detail"]


@pytest.mark.asyncio
async def test_call_apertus_falls_back_when_model_missing():
    """404 on the primary id must try the documented Public AI model. No network."""
    settings = Settings(
        hf_token="hf_test_token",
        apertus_base_url="https://router.huggingface.co/v1",
        apertus_model="swiss-ai/Apertus-v1.5-8B",
        apertus_timeout=10.0,
        apertus_fallback_model="swiss-ai/Apertus-8B-Instruct-2509:publicai",
    )
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        seen.append(body["model"])
        if body["model"] == "swiss-ai/Apertus-v1.5-8B":
            return httpx.Response(404, json={"error": "model not found"})
        assert request.headers.get("Authorization") == "Bearer hf_test_token"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"role": "assistant", "content": json.dumps(FAKE_BRIEF)}}
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        brief = await call_apertus(settings, "sample document text", client=client)
    assert seen == [
        "swiss-ai/Apertus-v1.5-8B",
        "swiss-ai/Apertus-8B-Instruct-2509:publicai",
    ]
    assert brief.summary.startswith("Vendor")
    assert len(brief.next_actions) == 5


@pytest.mark.asyncio
async def test_paid_status_does_not_try_fallback():
    settings = Settings(
        hf_token="hf_test_token",
        apertus_base_url="https://router.huggingface.co/v1",
        apertus_model="swiss-ai/Apertus-v1.5-8B",
        apertus_timeout=10.0,
        apertus_fallback_model="swiss-ai/Apertus-8B-Instruct-2509:publicai",
    )
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        seen.append(body["model"])
        return httpx.Response(402, text="Payment required. token hf_should_not_leak")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(RuntimeError, match="402") as exc:
            await call_apertus(settings, "sample document text", client=client)
    assert seen == ["swiss-ai/Apertus-v1.5-8B"]
    assert "hf_" not in str(exc.value) or "hf_REDACTED" in str(exc.value)
    assert "hf_should_not_leak" not in str(exc.value)


def test_local_endpoint_skips_fallback(monkeypatch):
    monkeypatch.setenv("APERTUS_BASE_URL", "http://127.0.0.1:8000/v1")
    monkeypatch.setenv("APERTUS_FALLBACK_MODEL", "swiss-ai/Apertus-8B-Instruct-2509:publicai")
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("APERTUS_API_KEY", raising=False)
    settings = load_settings()
    assert settings.is_local_endpoint
    assert settings.apertus_fallback_model == "swiss-ai/Apertus-8B-Instruct-2509:publicai"
    from sovereignbrief.llm import _models_to_try

    assert _models_to_try(settings) == [settings.apertus_model]
