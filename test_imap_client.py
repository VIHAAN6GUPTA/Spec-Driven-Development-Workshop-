from datetime import datetime
from email.message import EmailMessage

from email_assistant.imap_client import infer_imap_host, parse_raw_message


def test_infer_gmail_host():
    host, port = infer_imap_host("user@gmail.com")
    assert host == "imap.gmail.com"
    assert port == 993


def test_infer_outlook_host():
    host, port = infer_imap_host("user@outlook.com")
    assert host == "outlook.office365.com"


def test_infer_custom_domain():
    host, port = infer_imap_host("user@acme.corp")
    assert host == "imap.acme.corp"
    assert port == 993


def test_parse_raw_message():
    msg = EmailMessage()
    msg["From"] = "Boss <boss@company.com>"
    msg["Subject"] = "Project update"
    msg["Date"] = "Mon, 1 Jan 2024 12:00:00 +0000"
    msg.set_content("Please review the attached document by Friday.")
    raw = msg.as_bytes()
    parsed = parse_raw_message("1", raw)
    assert parsed.from_addr
    assert "Project update" in parsed.subject
    assert "review" in parsed.body_snippet.lower()
    assert isinstance(parsed.date, datetime)
