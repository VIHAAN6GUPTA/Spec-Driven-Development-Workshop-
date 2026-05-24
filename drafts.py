from __future__ import annotations

from email_assistant.config import Settings
from email_assistant.models import AnalysisResult


def _summary_from_snippet(result: AnalysisResult) -> str:
    msg = result.message
    snippet = msg.body_snippet[:120].strip()
    if snippet:
        return f"{msg.subject} — {snippet}"
    return msg.subject


def generate_drafts(settings: Settings, results: list[AnalysisResult]) -> list[AnalysisResult]:
    for result in results:
        if result.spam_label == "spam":
            continue
        if result.priority not in ("urgent", "important"):
            continue

        if not settings.use_llm:
            result.summary = _summary_from_snippet(result)
            result.draft_reply = None
            result.draft_note = (
                "Set OPENAI_API_KEY in .env for full AI-generated reply drafts."
            )
            continue

        summary, draft = _llm_draft(settings, result)
        result.summary = summary or _summary_from_snippet(result)
        result.draft_reply = draft
        result.draft_note = None
    return results


def _llm_draft(settings: Settings, result: AnalysisResult) -> tuple[str | None, str | None]:
    try:
        from openai import OpenAI

        kwargs = {"api_key": settings.openai_api_key}
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url
        client = OpenAI(**kwargs)
        msg = result.message
        prompt = (
            f"From: {msg.from_addr}\n"
            f"Subject: {msg.subject}\n"
            f"Priority: {result.priority}\n"
            f"Body:\n{msg.body_snippet[:1500]}\n\n"
            "Reply with JSON: {\"summary\": \"one line\", \"draft_reply\": \"professional reply body\"}"
        )
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You draft concise professional email replies. JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=400,
        )
        import json
        import re

        raw = resp.choices[0].message.content or "{}"
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            return data.get("summary"), data.get("draft_reply")
    except Exception:
        pass
    return None, None
