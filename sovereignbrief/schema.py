"""Fixed briefing schema returned by SovereignBrief."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class NextAction(BaseModel):
    action: str = Field(..., description="Concrete next step")
    owner: str = Field(default="Unassigned", description="Suggested owner role")
    due: str = Field(default="TBD", description="Suggested timing / deadline hint")


class Briefing(BaseModel):
    summary: str = Field(..., description="Short executive summary")
    risks: list[str] = Field(default_factory=list)
    decisions_needed: list[str] = Field(default_factory=list)
    next_actions: list[NextAction] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="Up to five concrete next actions",
    )
    open_questions: list[str] = Field(default_factory=list)
    second_language: Optional[str] = Field(
        default=None,
        description="Optional brief in the requested second language (plain text)",
    )
    second_language_code: Optional[str] = Field(
        default=None,
        description="ISO-ish code for second_language, e.g. hi or en",
    )


BRIEFING_JSON_SCHEMA_HINT = """{
  "summary": "string — 2-4 sentence executive summary",
  "risks": ["string", "..."],
  "decisions_needed": ["string", "..."],
  "next_actions": [
    {"action": "string", "owner": "role or Unassigned", "due": "timing hint or TBD"}
  ],
  "open_questions": ["string", "..."],
  "second_language": "string or null — full brief prose in the second language if requested",
  "second_language_code": "hi|en|de|null"
}"""
