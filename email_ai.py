#!/usr/bin/env python3
"""
Email AI Assistant
- Connects to Gmail via OAuth
- Classifies emails as spam / not spam
- Flags important & urgent emails
- AI-generates reply drafts for important emails
"""

import os
import json
import base64
import pickle
import re
import textwrap
from datetime import datetime

# ─── Dependency check ──────────────────────────────────────────────────────────
MISSING = []
try:
    import anthropic
except ImportError:
    MISSING.append("anthropic")

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
except ImportError:
    MISSING.append("google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.prompt import Prompt, Confirm
    from rich import box
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.markdown import Markdown
except ImportError:
    MISSING.append("rich")

if MISSING:
    print("\n❌  Missing packages. Run this first:\n")
    print(f"   pip install {' '.join(MISSING)}\n")
    exit(1)

# ─── Config ────────────────────────────────────────────────────────────────────
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
TOKEN_FILE = "token.pickle"
CREDENTIALS_FILE = "credentials.json"
MAX_EMAILS = 20          # how many recent emails to fetch
ANTHROPIC_MODEL = "claude-sonnet-4-20250514"

console = Console()

# ─── Auth ──────────────────────────────────────────────────────────────────────
def get_gmail_service():
    creds = None

    if not os.path.exists(CREDENTIALS_FILE):
        console.print(Panel(
            "[bold red]credentials.json not found![/]\n\n"
            "To set up Gmail access:\n"
            "1. Go to [link=https://console.cloud.google.com]console.cloud.google.com[/link]\n"
            "2. Create a project → Enable Gmail API\n"
            "3. OAuth consent screen → Add your email as test user\n"
            "4. Create OAuth credentials (Desktop app) → Download as [bold]credentials.json[/]\n"
            "5. Place credentials.json in the same folder as this script\n"
            "6. Run the script again",
            title="Setup Required",
            border_style="red"
        ))
        exit(1)

    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            with Progress(SpinnerColumn(), TextColumn("[cyan]Refreshing token..."), transient=True) as p:
                p.add_task("")
                creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            console.print("\n[cyan]Opening browser for Gmail login...[/]\n")
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)

    return build("gmail", "v1", credentials=creds)


# ─── Email fetching ────────────────────────────────────────────────────────────
def decode_body(payload):
    """Extract plain text from email payload."""
    body = ""
    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain":
                data = part["body"].get("data", "")
                if data:
                    body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                    break
            elif "parts" in part:
                body = decode_body(part)
                if body:
                    break
    else:
        data = payload.get("body", {}).get("data", "")
        if data:
            body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    return body[:2000]  # cap to avoid token explosion


def get_header(headers, name):
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def fetch_emails(service, max_results=MAX_EMAILS):
    results = service.users().messages().list(
        userId="me", maxResults=max_results, labelIds=["INBOX"]
    ).execute()
    messages = results.get("messages", [])
    emails = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[cyan]Fetching {task.description}"),
        transient=True,
        console=console
    ) as progress:
        task = progress.add_task(f"email 1/{len(messages)}", total=len(messages))
        for i, msg in enumerate(messages):
            progress.update(task, description=f"email {i+1}/{len(messages)}", advance=1)
            full = service.users().messages().get(
                userId="me", messageId=msg["id"], format="full"
            ).execute()
            headers = full["payload"]["headers"]
            body = decode_body(full["payload"])
            emails.append({
                "id": msg["id"],
                "subject": get_header(headers, "Subject") or "(no subject)",
                "from": get_header(headers, "From"),
                "date": get_header(headers, "Date"),
                "snippet": full.get("snippet", ""),
                "body": body,
                "labels": full.get("labelIds", []),
            })
    return emails


# ─── AI Analysis ───────────────────────────────────────────────────────────────
def analyze_emails(emails):
    client = anthropic.Anthropic()

    email_list = "\n\n".join([
        f"EMAIL #{i+1}\n"
        f"From: {e['from']}\n"
        f"Subject: {e['subject']}\n"
        f"Date: {e['date']}\n"
        f"Body snippet: {e['snippet'][:500]}"
        for i, e in enumerate(emails)
    ])

    system_prompt = """You are an expert email classifier. For each email provided, analyze it and respond ONLY with a valid JSON array.

Each element in the array must have:
- "index": (int) the email number (1-based)
- "is_spam": (bool) true if this looks like spam, marketing, newsletter, phishing, or promotional content
- "is_important": (bool) true if this requires attention (work, bills, personal relationships, official)
- "is_urgent": (bool) true if this needs a response within 24 hours
- "urgency_reason": (string) brief reason if urgent, else ""
- "summary": (string) 1-sentence summary of what the email is about
- "spam_reason": (string) why it's spam if is_spam is true, else ""
- "category": (string) one of: "spam", "newsletter", "work", "personal", "finance", "alert", "social", "other"

Return ONLY the JSON array with no markdown, no explanation, no preamble."""

    with Progress(SpinnerColumn(), TextColumn("[cyan]Analyzing emails with AI..."), transient=True) as p:
        p.add_task("")
        message = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=4000,
            messages=[{
                "role": "user",
                "content": f"Classify these {len(emails)} emails:\n\n{email_list}"
            }],
            system=system_prompt
        )

    raw = message.content[0].text.strip()
    raw = re.sub(r"```json|```", "", raw).strip()
    return json.loads(raw)


def generate_reply(email, client=None):
    if client is None:
        client = anthropic.Anthropic()

    prompt = f"""Write a professional, concise email reply to this email. 
Be helpful and address the key points. Keep it short (3-5 sentences max unless detail is truly needed).

FROM: {email['from']}
SUBJECT: {email['subject']}
EMAIL CONTENT:
{email['body'] or email['snippet']}

Write ONLY the reply body — no subject line, no "Here is a reply:" preamble. Start directly with the reply."""

    with Progress(SpinnerColumn(), TextColumn("[cyan]Drafting reply..."), transient=True) as p:
        p.add_task("")
        message = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
    return message.content[0].text.strip()


# ─── Display ───────────────────────────────────────────────────────────────────
CATEGORY_COLORS = {
    "spam": "red",
    "newsletter": "yellow",
    "work": "blue",
    "personal": "green",
    "finance": "cyan",
    "alert": "magenta",
    "social": "bright_blue",
    "other": "white",
}

CATEGORY_ICONS = {
    "spam": "🚫",
    "newsletter": "📰",
    "work": "💼",
    "personal": "👤",
    "finance": "💰",
    "alert": "🔔",
    "social": "💬",
    "other": "📧",
}


def display_summary_table(emails, analyses):
    table = Table(
        title=f"📬  Inbox Analysis — {len(emails)} emails",
        box=box.ROUNDED,
        show_lines=True,
        highlight=True,
        title_style="bold white"
    )
    table.add_column("#", style="dim", width=3, justify="right")
    table.add_column("From", style="cyan", max_width=28)
    table.add_column("Subject", max_width=35)
    table.add_column("Category", justify="center", width=12)
    table.add_column("Status", justify="center", width=16)
    table.add_column("Summary", max_width=40)

    for a in analyses:
        i = a["index"] - 1
        e = emails[i]
        cat = a["category"]
        color = CATEGORY_COLORS.get(cat, "white")
        icon = CATEGORY_ICONS.get(cat, "📧")

        # status badges
        badges = []
        if a["is_spam"]:
            badges.append("[red]⛔ SPAM[/]")
        if a["is_urgent"]:
            badges.append("[bold red]🚨 URGENT[/]")
        elif a["is_important"]:
            badges.append("[yellow]⭐ IMPORTANT[/]")
        status = "  ".join(badges) if badges else "[dim]—[/]"

        sender = re.sub(r"<.*?>", "", e["from"]).strip()[:28]
        subject = e["subject"][:35]

        table.add_row(
            str(a["index"]),
            sender,
            subject,
            f"[{color}]{icon} {cat}[/]",
            status,
            a["summary"][:40],
        )

    console.print()
    console.print(table)


def display_stats(analyses):
    total = len(analyses)
    spam = sum(1 for a in analyses if a["is_spam"])
    important = sum(1 for a in analyses if a["is_important"] and not a["is_spam"])
    urgent = sum(1 for a in analyses if a["is_urgent"] and not a["is_spam"])
    clean = total - spam

    console.print()
    console.print(Panel(
        f"  📊  [bold]Inbox Stats[/bold]\n\n"
        f"  Total scanned : [white]{total}[/]\n"
        f"  🚫 Spam        : [red]{spam}[/] ({spam*100//total}%)\n"
        f"  ✅ Clean       : [green]{clean}[/]\n"
        f"  ⭐ Important   : [yellow]{important}[/]\n"
        f"  🚨 Urgent      : [bold red]{urgent}[/]",
        border_style="cyan",
        expand=False
    ))


def interactive_menu(emails, analyses, client):
    urgent_important = [a for a in analyses if (a["is_important"] or a["is_urgent"]) and not a["is_spam"]]

    while True:
        console.print("\n[bold cyan]━━━ What would you like to do? ━━━[/]")
        console.print("  [1] View important & urgent emails in detail")
        console.print("  [2] View spam emails")
        console.print("  [3] Generate AI reply for an email")
        console.print("  [4] View all emails")
        console.print("  [5] Quit")
        console.print()

        choice = Prompt.ask("[bold]Enter choice[/]", choices=["1", "2", "3", "4", "5"])

        if choice == "1":
            if not urgent_important:
                console.print("[dim]No important or urgent emails found.[/]")
                continue
            console.print(f"\n[bold yellow]⭐ Important / 🚨 Urgent Emails ({len(urgent_important)})[/]\n")
            for a in urgent_important:
                e = emails[a["index"] - 1]
                console.print(Panel(
                    f"[bold]From:[/]    {e['from']}\n"
                    f"[bold]Subject:[/] {e['subject']}\n"
                    f"[bold]Date:[/]    {e['date']}\n"
                    f"[bold]Summary:[/] {a['summary']}\n"
                    + (f"[bold red]Urgent:[/] {a['urgency_reason']}\n" if a["is_urgent"] else "")
                    + f"\n[dim]{e['snippet'][:300]}...[/]",
                    title=f"Email #{a['index']} — {'🚨 URGENT' if a['is_urgent'] else '⭐ Important'}",
                    border_style="red" if a["is_urgent"] else "yellow"
                ))

        elif choice == "2":
            spam_list = [a for a in analyses if a["is_spam"]]
            if not spam_list:
                console.print("[dim]No spam detected.[/]")
                continue
            console.print(f"\n[bold red]🚫 Spam Emails ({len(spam_list)})[/]\n")
            for a in spam_list:
                e = emails[a["index"] - 1]
                console.print(
                    f"  [red]#{a['index']}[/] [dim]{e['from'][:40]}[/] → "
                    f"[italic]{e['subject'][:50]}[/] — "
                    f"[dim red]{a['spam_reason']}[/]"
                )

        elif choice == "3":
            num = Prompt.ask(f"Enter email number (1–{len(emails)})")
            try:
                idx = int(num) - 1
                if idx < 0 or idx >= len(emails):
                    raise ValueError
            except ValueError:
                console.print("[red]Invalid number.[/]")
                continue

            e = emails[idx]
            a = next((x for x in analyses if x["index"] == idx + 1), None)

            console.print(f"\n[bold]Generating reply for:[/] {e['subject']}")
            reply = generate_reply(e, client)
            console.print(Panel(
                reply,
                title=f"✉️  Suggested Reply — Email #{idx+1}",
                border_style="green"
            ))
            console.print("[dim](Copy the reply above and send from your Gmail)[/]")

        elif choice == "4":
            display_summary_table(emails, analyses)

        elif choice == "5":
            console.print("\n[cyan]Bye! 👋[/]\n")
            break


# ─── Main ──────────────────────────────────────────────────────────────────────
def main():
    console.print(Panel(
        "[bold cyan]Email AI Assistant[/bold cyan]\n"
        "[dim]Spam detection · Priority inbox · AI-generated replies[/dim]",
        border_style="cyan"
    ))

    # Check API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        console.print(Panel(
            "[bold yellow]ANTHROPIC_API_KEY not set![/]\n\n"
            "Set it with:\n"
            "  [bold]export ANTHROPIC_API_KEY=sk-ant-...[/]  (Mac/Linux)\n"
            "  [bold]set ANTHROPIC_API_KEY=sk-ant-...[/]     (Windows CMD)\n\n"
            "Get your key at: [link=https://console.anthropic.com]console.anthropic.com[/link]",
            title="API Key Missing",
            border_style="yellow"
        ))
        exit(1)

    client = anthropic.Anthropic()

    # Gmail auth
    console.print("\n[cyan]Connecting to Gmail...[/]")
    service = get_gmail_service()
    console.print("[green]✓ Gmail connected[/]")

    # Fetch
    count = Prompt.ask(
        f"\nHow many recent emails to analyze? (1–50)",
        default="20"
    )
    try:
        count = max(1, min(50, int(count)))
    except ValueError:
        count = 20

    emails = fetch_emails(service, max_results=count)
    console.print(f"[green]✓ Fetched {len(emails)} emails[/]")

    # Analyze
    analyses = analyze_emails(emails)
    console.print(f"[green]✓ AI analysis complete[/]")

    # Display
    display_stats(analyses)
    display_summary_table(emails, analyses)

    # Interactive mode
    interactive_menu(emails, analyses, client)


if __name__ == "__main__":
    main()
