from __future__ import annotations

from datetime import datetime, timedelta, timezone

from email_assistant.config import Settings
from email_assistant.heuristics import keyword_priority_hint
from email_assistant.models import AnalysisResult, Priority


def _sender_in_allowlist(from_addr: str, allowlist: list[str]) -> bool:
    from_lower = from_addr.lower()
    for sender in allowlist:
        if sender in from_lower:
            return True
    return False


def _is_recent(message_date: datetime | None, hours: int = 24) -> bool:
    if message_date is None:
        return False
    if message_date.tzinfo is None:
        message_date = message_date.replace(tzinfo=timezone.utc)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    return message_date >= cutoff


def triage_message(settings: Settings, result: AnalysisResult) -> AnalysisResult:
    if result.spam_label == "spam":
        result.priority = None
        return result

    priority: Priority = "normal"
    reasons: list[str] = []

    kw_level, kw_reason = keyword_priority_hint(result.message)
    if kw_level == "urgent":
        priority = "urgent"
        reasons.append(kw_reason)
    elif kw_level == "important" and priority != "urgent":
        priority = "important"
        reasons.append(kw_reason)

    if _sender_in_allowlist(result.message.from_addr, settings.important_senders):
        if priority == "normal":
            priority = "important"
        reasons.append("sender in IMPORTANT_SENDERS")

    if _is_recent(result.message.date) and priority == "normal":
        # Recency alone does not elevate; noted for LLM context only
        pass

    if result.llm_priority and result.spam_label == "not_spam":
        order = {"urgent": 3, "important": 2, "normal": 1}
        if order.get(result.llm_priority, 0) > order.get(priority, 0):
            priority = result.llm_priority
            reasons.append(f"LLM priority: {result.llm_priority}")

    result.priority = priority
    if reasons and result.spam_reason:
        result.spam_reason = result.spam_reason  # keep spam reason separate
    return result
