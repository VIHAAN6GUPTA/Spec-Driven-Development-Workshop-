from __future__ import annotations

from email_assistant.classifier import classify_message
from email_assistant.config import load_settings
from email_assistant.drafts import generate_drafts
from email_assistant.imap_client import ImapClient
from email_assistant.output import print_report, write_json_report
from email_assistant.triage import triage_message


def run(argv: list[str] | None = None) -> int:
    settings = load_settings(argv)
    client = ImapClient(
        settings.email_address,
        settings.email_password,
        host=settings.imap_host,
        port=settings.imap_port,
    )

    print(f"Connecting to {client.host} as {settings.email_address}...")
    conn = client.connect()
    try:
        messages = client.fetch_recent_messages(conn, settings.max_messages)
    finally:
        try:
            conn.logout()
        except Exception:
            pass

    print(f"Fetched {len(messages)} message(s).\n")

    results = []
    for msg in messages:
        result = classify_message(settings, msg)
        result = triage_message(settings, result)
        results.append(result)

    generate_drafts(settings, results)
    print_report(results)

    if settings.output_path:
        write_json_report(results, settings.output_path)

    return 0


def main() -> None:
    raise SystemExit(run())
