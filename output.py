from __future__ import annotations

import json
from pathlib import Path

from email_assistant.models import AnalysisResult


def print_report(results: list[AnalysisResult]) -> None:
    spam = [r for r in results if r.spam_label == "spam"]
    inbox = [r for r in results if r.spam_label == "not_spam"]
    drafts = [
        r
        for r in results
        if r.spam_label == "not_spam" and r.priority in ("urgent", "important")
    ]

    print("\n" + "=" * 60)
    print("SPAM")
    print("=" * 60)
    if not spam:
        print("(none)")
    for r in spam:
        m = r.message
        print(f"  [{m.id}] {m.from_addr}")
        print(f"    Subject: {m.subject}")
        print(f"    Reason:  {r.spam_reason}")
        print()

    print("=" * 60)
    print("INBOX (not spam)")
    print("=" * 60)
    if not inbox:
        print("(none)")
    for r in inbox:
        m = r.message
        print(f"  [{m.id}] {m.from_addr}  [{r.priority}]")
        print(f"    Subject: {m.subject}")
        print()

    print("=" * 60)
    print("DRAFTS (urgent / important)")
    print("=" * 60)
    if not drafts:
        print("(none)")
    for r in drafts:
        m = r.message
        print(f"  [{m.id}] {m.from_addr}  [{r.priority}]")
        print(f"    Subject: {m.subject}")
        print(f"    Summary: {r.summary or '(no summary)'}")
        if r.draft_reply:
            print(f"    Draft reply:\n{r.draft_reply}")
        if r.draft_note:
            print(f"    Note: {r.draft_note}")
        print()


def write_json_report(results: list[AnalysisResult], path: str) -> None:
    payload = {
        "spam": [
            {
                "id": r.message.id,
                "from": r.message.from_addr,
                "subject": r.message.subject,
                "reason": r.spam_reason,
            }
            for r in results
            if r.spam_label == "spam"
        ],
        "inbox": [
            {
                "id": r.message.id,
                "from": r.message.from_addr,
                "subject": r.message.subject,
                "priority": r.priority,
            }
            for r in results
            if r.spam_label == "not_spam"
        ],
        "drafts": [
            {
                "id": r.message.id,
                "from": r.message.from_addr,
                "subject": r.message.subject,
                "priority": r.priority,
                "summary": r.summary,
                "draft_reply": r.draft_reply,
                "note": r.draft_note,
            }
            for r in results
            if r.spam_label == "not_spam" and r.priority in ("urgent", "important")
        ],
    }
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nReport written to {path}")
