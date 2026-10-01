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
