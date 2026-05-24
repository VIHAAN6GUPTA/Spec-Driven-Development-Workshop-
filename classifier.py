from __future__ import annotations

from email_assistant.config import Settings
from email_assistant.heuristics import score_spam
from email_assistant.llm_classifier import analyze_with_llm
from email_assistant.models import AnalysisResult, Message, SpamLabel


def classify_message(settings: Settings, message: Message) -> AnalysisResult:
    heuristic = score_spam(message)
    label: SpamLabel = heuristic.label
    reason = f"heuristic (score={heuristic.score}): {heuristic.reason}"

    llm_priority = None
    if settings.use_llm:
        llm_label, llm_reason, llm_priority = analyze_with_llm(settings, message)
        if llm_label is not None:
            if llm_label == "spam" or heuristic.label == "spam":
                label = "spam"
                reason = f"{reason}; LLM: {llm_reason}"
            else:
                label = "not_spam"
                reason = f"{reason}; LLM: {llm_reason}"

    return AnalysisResult(
        message=message,
        spam_label=label,
        spam_reason=reason,
        llm_priority=llm_priority,
    )
