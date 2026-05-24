from datetime import datetime, timezone

from email_assistant.classifier import classify_message
from email_assistant.config import Settings
from email_assistant.heuristics import score_spam
from email_assistant.models import Message


def _msg(subject: str, body: str = "", **headers) -> Message:
    return Message(
        id="1",
        from_addr="sender@example.com",
        subject=subject,
        date=datetime.now(timezone.utc),
        body_snippet=body,
        headers=headers,
    )


def test_spam_lottery_keywords():
    result = score_spam(
        _msg("You have WON the lottery!!!", "click here now for free money")
    )
    assert result.label == "spam"
    assert result.score >= 3


def test_legitimate_mail_not_spam():
    result = score_spam(
        _msg(
            "Meeting tomorrow",
            "Hi, can we meet at 10am to discuss the project?",
        )
    )
    assert result.label == "not_spam"


def test_classifier_without_llm():
    settings = Settings(
        email_address="u@gmail.com",
        email_password="x",
        imap_host=None,
        imap_port=993,
        max_messages=10,
        openai_api_key=None,
        openai_base_url=None,
        important_senders=[],
        use_llm=False,
        output_path=None,
    )
    spam_result = classify_message(
        settings,
        _msg("WINNER!!!", "viagra lottery click here now"),
    )
    assert spam_result.spam_label == "spam"

    ok_result = classify_message(
        settings,
        _msg("Lunch?", "Want to grab lunch on Tuesday?"),
    )
    assert ok_result.spam_label == "not_spam"
