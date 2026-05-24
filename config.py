from __future__ import annotations

import argparse
import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Settings:
    email_address: str
    email_password: str
    imap_host: str | None
    imap_port: int
    max_messages: int
    openai_api_key: str | None
    openai_base_url: str | None
    important_senders: list[str]
    use_llm: bool
    output_path: str | None


def _parse_sender_list(value: str | None) -> list[str]:
    if not value or not value.strip():
        return []
    return [s.strip().lower() for s in value.split(",") if s.strip()]


def load_settings(argv: list[str] | None = None) -> Settings:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Analyze inbox: classify spam, triage priority, draft replies."
    )
    parser.add_argument("--email", help="Email address (overrides EMAIL_ADDRESS)")
    parser.add_argument("--max", type=int, help="Max messages to fetch")
    parser.add_argument("--no-llm", action="store_true", help="Disable LLM features")
    parser.add_argument("--output", help="Write JSON report to this path")
    args = parser.parse_args(argv)

    email = (args.email or os.getenv("EMAIL_ADDRESS", "")).strip()
    password = os.getenv("EMAIL_PASSWORD", "").strip()
    if not email:
        raise SystemExit(
            "Missing email address. Set EMAIL_ADDRESS in .env or pass --email."
        )
    if not password:
        raise SystemExit(
            "Missing password. Set EMAIL_PASSWORD in .env (use an app-specific password)."
        )

    max_messages = args.max
    if max_messages is None:
        max_messages = int(os.getenv("MAX_MESSAGES", "50"))

    api_key = os.getenv("OPENAI_API_KEY", "").strip() or None
    use_llm = not args.no_llm and bool(api_key)

    return Settings(
        email_address=email,
        email_password=password,
        imap_host=os.getenv("IMAP_HOST", "").strip() or None,
        imap_port=int(os.getenv("IMAP_PORT", "993")),
        max_messages=max_messages,
        openai_api_key=api_key,
        openai_base_url=os.getenv("OPENAI_BASE_URL", "").strip() or None,
        important_senders=_parse_sender_list(os.getenv("IMPORTANT_SENDERS")),
        use_llm=use_llm,
        output_path=args.output,
    )
