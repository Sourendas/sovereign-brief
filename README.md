# SovereignBrief

**Hack Apertus 2026 — Track 2B Own Project**

Paste a messy policy/ops document (or upload a small PDF) → get a short multilingual **action brief** with risks, decisions needed, five next actions, and open questions — powered by Switzerland’s open **Apertus** LLM.

Model id (preferred, from the model card): [`swiss-ai/Apertus-v1.5-8B`](https://huggingface.co/swiss-ai/Apertus-v1.5-8B)

As of 2026-10-02 that id has **no** Hugging Face Inference Provider mapping (absent from the router model list; a chat call returns HTTP 400). SovereignBrief then retries **one** documented live Apertus route and stops:

- `swiss-ai/Apertus-8B-Instruct-2509:publicai` (Public AI on the HF router)

That route is **not** marked `is_free` on the router (about $0.10 / $0.20 per million input/output tokens). It is meant to draw only on the **included** free-account monthly Inference Providers credits (about $0.10). This project does **not** buy credits, add a card, or switch to another provider. HTTP 402 stops the call.

Override with `APERTUS_MODEL`. Set `APERTUS_FALLBACK_MODEL=off` to disable the retry. A local `APERTUS_BASE_URL` never uses the fallback.

## Why Track 2B

- New project started in the hackathon window (1–16 Oct 2026).
- Demonstrates **adoption** of Apertus on a real ops workflow (not red-teaming).
- Same stack can point at a **local / self-hosted** OpenAI-compatible Apertus endpoint (sovereign path).

## Requirements

- Python 3.11+ recommended
- Free Hugging Face account + token with Inference Providers access for the default remote endpoint
- **Zero spend**: do not put paid API keys in `.env`

## Quick start (local)

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env — set HF_TOKEN=hf_...  (never commit .env)
uvicorn main:app --reload --host 127.0.0.1 --port 8080
```

Open http://127.0.0.1:8080/

- UI: paste text, optional second language (EN↔HI / DE), optional small PDF
- Health: `GET /api/health`
- Sample fixture: `GET /api/sample`

If `HF_TOKEN` is missing and you are still on the remote HF router, the API returns **503** with a clear message. Inference is not pretended to work without a token.

## Sovereign / local endpoint path

Run Apertus yourself (e.g. Swiss AI’s vLLM image) so the OpenAI-compatible API listens locally, then:

```bash
# .env
HF_TOKEN=                 # optional for true local
APERTUS_BASE_URL=http://127.0.0.1:8000/v1
APERTUS_MODEL=swiss-ai/Apertus-v1.5-8B
```

Example local serve (from the model card; needs your own GPU — not required for the HF free-tier demo):

```bash
vllm serve swiss-ai/Apertus-v1.5-8B \
  --chat-template-content-format string \
  --gpu-memory-utilization 0.6 \
  --max-model-len 8192
```

SovereignBrief only needs `POST {APERTUS_BASE_URL}/chat/completions`. No closed US SaaS model is required at runtime.

## Briefing schema

```json
{
  "summary": "string",
  "risks": ["string"],
  "decisions_needed": ["string"],
  "next_actions": [
    {"action": "string", "owner": "string", "due": "string"}
  ],
  "open_questions": ["string"],
  "second_language": "string|null",
  "second_language_code": "hi|en|de|null"
}
```

`next_actions` is normalized to five items.

## Tests

```bash
pip install -r requirements.txt
pytest -q
```

Tests mock the LLM HTTP call; they do not call paid APIs and do not need a real `HF_TOKEN`.

## Project layout

```
main.py                 # FastAPI + static UI
sovereignbrief/         # config, LLM client, schema, PDF extract
static/index.html       # paste / upload UI
samples/sample_policy.txt
tests/
.env.example
requirements.txt
```

## License

MIT — use, copy, modify, and distribute freely; keep the copyright notice. This scaffold is intended as an open, reusable Track 2B prototype.

```
MIT License

Copyright (c) 2026 Souren Das / SovereignBrief contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```
