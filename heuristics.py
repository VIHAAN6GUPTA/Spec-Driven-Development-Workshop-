from __future__ import annotations

import re
from dataclasses import dataclass

from email_assistant.models import Message, SpamLabel

SPAM_KEYWORDS = [
    "winner",
    "congratulations",
    "lottery",
    "viagra",
    "crypto giveaway",
    "click here now",
    "act now",
    "limited time offer",
    "nigerian prince",
    "free money",
    "verify your account immediately",
    "you have won",
    "unclaimed funds",
]

URGENT_KEYWORDS = [
    "urgent",
    "asap",
    "immediate",
    "immediate action",
    "time sensitive",
    "deadline today",
    "respond today",
]

IMPORTANT_KEYWORDS = [
    "action required",
    "deadline",
    "invoice",
    "payment due",
    "security alert",
    "password reset",
    "interview",
    "offer letter",
    "contract",
]

URL_PATTERN = re.compile(r"https?://[^\s]+", re.I)


@dataclass
class HeuristicSpamResult:
    label: SpamLabel
    score: int
    reason: str


def score_spam(message: Message) -> HeuristicSpamResult:
    score = 0
    reasons: list[str] = []
    text = f"{message.subject} {message.body_snippet}".lower()

    for kw in SPAM_KEYWORDS:
        if kw in text:
            score += 2
            reasons.append(f"spam keyword: {kw}")

    if message.subject.isupper() and len(message.subject) > 10:
        score += 2
        reasons.append("subject is all caps")

    urls = URL_PATTERN.findall(text)
    if len(urls) >= 3:
        score += 2
        reasons.append(f"{len(urls)} links in body")

    precedence = message.headers.get("Precedence", "").lower()
    if precedence in ("bulk", "junk", "list"):
        score += 2
        reasons.append(f"Precedence: {precedence}")

    if message.headers.get("List-Unsubscribe"):
        score += 1
        reasons.append("bulk mail header (List-Unsubscribe)")

    if "!!!" in message.subject or "FREE" in message.subject.upper():
        score += 1
        reasons.append("promotional subject pattern")

    label: SpamLabel = "spam" if score >= 3 else "not_spam"
    reason = "; ".join(reasons) if reasons else "no spam signals detected"
    return HeuristicSpamResult(label=label, score=score, reason=reason)


def keyword_priority_hint(message: Message) -> tuple[str | None, str]:
    """Return ('urgent'|'important'|None, reason) from keywords."""
    text = f"{message.subject} {message.body_snippet}".lower()
    for kw in URGENT_KEYWORDS:
        if kw in text:
            return "urgent", f"urgent keyword: {kw}"
    for kw in IMPORTANT_KEYWORDS:
        if kw in text:
            return "important", f"important keyword: {kw}"
    return None, ""
