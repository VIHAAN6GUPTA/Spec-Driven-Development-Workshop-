from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

SpamLabel = Literal["spam", "not_spam"]
Priority = Literal["urgent", "important", "normal"]


@dataclass
class Message:
    id: str
    from_addr: str
    subject: str
    date: datetime | None
    body_snippet: str
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class AnalysisResult:
    message: Message
    spam_label: SpamLabel
    spam_reason: str
    priority: Priority | None = None
    summary: str | None = None
    draft_reply: str | None = None
    draft_note: str | None = None
    llm_priority: Priority | None = None
