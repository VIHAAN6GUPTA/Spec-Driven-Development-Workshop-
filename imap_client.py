from __future__ import annotations

import email
import imaplib
import re
from datetime import datetime
from email.header import decode_header
from email.utils import parsedate_to_datetime

from email_assistant.models import Message

# domain -> (host, port)
DEFAULT_IMAP: dict[str, tuple[str, int]] = {
    "gmail.com": ("imap.gmail.com", 993),
    "googlemail.com": ("imap.gmail.com", 993),
    "outlook.com": ("outlook.office365.com", 993),
    "hotmail.com": ("outlook.office365.com", 993),
    "live.com": ("outlook.office365.com", 993),
    "yahoo.com": ("imap.mail.yahoo.com", 993),
    "icloud.com": ("imap.mail.me.com", 993),
}


def infer_imap_host(email_address: str) -> tuple[str, int]:
    domain = email_address.rsplit("@", 1)[-1].lower()
    if domain in DEFAULT_IMAP:
        return DEFAULT_IMAP[domain]
    return (f"imap.{domain}", 993)


def _decode_header_value(value: str | None) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    chunks: list[str] = []
    for part, charset in parts:
        if isinstance(part, bytes):
            chunks.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            chunks.append(part)
    return "".join(chunks)


def _extract_body_snippet(msg: email.message.Message, limit: int = 500) -> str:
    text_parts: list[str] = []
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain" and "attachment" not in str(
                part.get("Content-Disposition", "")
            ):
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    text_parts.append(
                        payload.decode(charset, errors="replace")
                    )
    else:
        payload = msg.get_payload(decode=True)
        if payload and msg.get_content_type() == "text/plain":
            charset = msg.get_content_charset() or "utf-8"
            text_parts.append(payload.decode(charset, errors="replace"))
    body = " ".join(text_parts)
    body = re.sub(r"\s+", " ", body).strip()
    return body[:limit]


def parse_raw_message(msg_id: str, raw: bytes) -> Message:
    msg = email.message_from_bytes(raw)
    subject = _decode_header_value(msg.get("Subject"))
    from_addr = _decode_header_value(msg.get("From"))
    date_hdr = msg.get("Date")
    try:
        date = parsedate_to_datetime(date_hdr) if date_hdr else None
    except (TypeError, ValueError):
        date = None
    headers = {
        k: v
        for k, v in msg.items()
        if k.lower() in ("precedence", "list-unsubscribe", "x-spam-flag")
    }
    return Message(
        id=msg_id,
        from_addr=from_addr,
        subject=subject or "(no subject)",
        date=date,
        body_snippet=_extract_body_snippet(msg),
        headers=headers,
    )


class ImapClient:
    def __init__(
        self,
        email_address: str,
        password: str,
        host: str | None = None,
        port: int = 993,
    ) -> None:
        self.email_address = email_address
        self.password = password
        if host:
            self.host, self.port = host, port
        else:
            self.host, self.port = infer_imap_host(email_address)

    def connect(self) -> imaplib.IMAP4_SSL:
        try:
            conn = imaplib.IMAP4_SSL(self.host, self.port)
            conn.login(self.email_address, self.password)
            return conn
        except imaplib.IMAP4.error as exc:
            raise ConnectionError(
                f"IMAP authentication failed for {self.email_address} at {self.host}. "
                "Check EMAIL_PASSWORD (use an app-specific password) and that IMAP is enabled."
            ) from exc
        except OSError as exc:
            raise ConnectionError(
                f"Could not connect to {self.host}:{self.port}. "
                f"Check network and IMAP_HOST if using a custom provider."
            ) from exc

    def fetch_recent_messages(
        self, conn: imaplib.IMAP4_SSL, limit: int
    ) -> list[Message]:
        conn.select("INBOX", readonly=True)
        _, data = conn.search(None, "ALL")
        if not data or not data[0]:
            return []
        ids = data[0].split()
        recent_ids = ids[-limit:] if len(ids) > limit else ids
        messages: list[Message] = []
        for msg_id in reversed(recent_ids):
            _, msg_data = conn.fetch(msg_id, "(RFC822)")
            if not msg_data or not msg_data[0]:
                continue
            part = msg_data[0]
            if isinstance(part, tuple) and len(part) >= 2:
                raw = part[1]
                if isinstance(raw, bytes):
                    messages.append(
                        parse_raw_message(msg_id.decode(), raw)
                    )
        return messages
