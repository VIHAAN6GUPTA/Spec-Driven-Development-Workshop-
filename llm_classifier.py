from __future__ import annotations

import json
import re

from email_assistant.config import Settings
from email_assistant.models import Message, Priority, SpamLabel

SYSTEM_PROMPT = """You analyze email messages. Respond with JSON only, no markdown.
Fields:
- spam: boolean (true if spam/phishing/promotional junk)
- spam_reason: short string
- priority: one of "urgent", "important", "normal" (only for non-spam)
"""


def _client(settings: Settings):
    from openai import OpenAI

    kwargs = {"api_key": settings.openai_api_key}
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    return OpenAI(**kwargs)


def _parse_json(text: str) -> dict:
    text = text.strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)
    return json.loads(text)


def analyze_with_llm(
    settings: Settings, message: Message
) -> tuple[SpamLabel | None, str | None, Priority | None]:
    """Returns (spam_label, reason, priority) or Nones on failure."""
    if not settings.use_llm or not settings.openai_api_key:
        return None, None, None
    user_content = (
        f"From: {message.from_addr}\n"
        f"Subject: {message.subject}\n"
        f"Body snippet: {message.body_snippet[:800]}\n"
        f"Headers: {message.headers}"
    )
    try:
        client = _client(settings)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.2,
            max_tokens=200,
        )
        raw = resp.choices[0].message.content or "{}"
        data = _parse_json(raw)
        spam = bool(data.get("spam", False))
        label: SpamLabel = "spam" if spam else "not_spam"
        reason = str(data.get("spam_reason", "LLM classification"))
        priority_raw = str(data.get("priority", "normal")).lower()
        priority: Priority = (
            priority_raw
            if priority_raw in ("urgent", "important", "normal")
            else "normal"
        )
        if label == "spam":
            priority = "normal"
        return label, reason, priority
    except Exception:
        return None, None, None
