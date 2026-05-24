from datetime import datetime, timezone

from email_assistant.config import Settings
from email_assistant.models import AnalysisResult, Message
from email_assistant.triage import triage_message


def _settings(**kwargs) -> Settings:
    base = dict(
        email_address="u@gmail.com",
        email_password="x",
        imap_host=None,
        imap_port=993,
        max_messages=10,
        openai_api_key=None,
        openai_base_url=None,
        important_senders=["boss@company.com"],
        use_llm=False,
        output_path=None,
    )
    base.update(kwargs)
    return Settings(**base)


def _result(subject: str, body: str, from_addr: str = "a@b.com") -> AnalysisResult:
    return AnalysisResult(
        message=Message(
            id="1",
            from_addr=from_addr,
            subject=subject,
            date=datetime.now(timezone.utc),
            body_snippet=body,
        ),
        spam_label="not_spam",
        spam_reason="ok",
    )


def test_urgent_keyword():
    r = triage_message(_settings(), _result("URGENT: server down", "please fix asap"))
    assert r.priority == "urgent"


def test_important_sender_allowlist():
    r = triage_message(
        _settings(),
        _result("Hello", "weekly sync", from_addr="Boss <boss@company.com>"),
    )
    assert r.priority == "important"


def test_normal_routine():
    r = triage_message(_settings(), _result("Newsletter", "here is this week's update"))
    assert r.priority == "normal"


def test_spam_skips_triage():
    r = AnalysisResult(
        message=Message("1", "x@y.com", "spam", None, "buy now"),
        spam_label="spam",
        spam_reason="spam",
    )
    r = triage_message(_settings(), r)
    assert r.priority is None
