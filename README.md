# 📬 Email AI Assistant

Connects to your Gmail inbox, classifies spam, highlights important/urgent emails, and drafts AI replies — all in your terminal.

---

## ⚡ Quick Setup (5 minutes)

### Step 1 — Install dependencies

```bash
pip install -r requirements.txt
```

---

### Step 2 — Set your Anthropic API key

**Mac/Linux:**
```bash
export ANTHROPIC_API_KEY=sk-ant-your-key-here
```

**Windows CMD:**
```cmd
set ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Get your key at: https://console.anthropic.com

---

### Step 3 — Set up Gmail API access

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or select existing)
3. Go to **APIs & Services → Library** → Search for **Gmail API** → Enable it
4. Go to **APIs & Services → OAuth consent screen**
   - Choose **External**
   - Fill in app name (e.g. "Email AI")
   - Under **Test users**, add your Gmail address
5. Go to **APIs & Services → Credentials**
   - Click **Create Credentials → OAuth client ID**
   - Application type: **Desktop app**
   - Download the JSON file
6. Rename the downloaded file to `credentials.json` and place it in this folder

---

### Step 4 — Run the app

```bash
python email_ai.py
```

On first run, a browser window will open asking you to authorize Gmail access. After that, a `token.pickle` file is saved so you don't need to log in again.

---

## 🎯 Features

| Feature | Description |
|---------|-------------|
| 🚫 Spam detection | AI flags spam, phishing, newsletters |
| ⭐ Important emails | Identifies emails needing attention |
| 🚨 Urgent alerts | Highlights emails needing a reply within 24h |
| ✉️ AI reply drafts | Claude writes a professional reply for any email |
| 📊 Stats summary | Inbox breakdown by category |

---

## 🔒 Privacy

- Your emails are sent to Claude AI (Anthropic) for analysis
- Only the subject, sender, and first ~500 chars of each email are sent
- No emails are stored or saved by this script
- OAuth token is stored locally in `token.pickle`

---

## 🛠 Troubleshooting

**"credentials.json not found"** — Follow Step 3 above

**"ANTHROPIC_API_KEY not set"** — Run the export command in Step 2

**Browser doesn't open for auth** — Run `python email_ai.py` in a terminal (not an IDE), or try `python -m webbrowser` to check your browser setup

**"Access blocked: This app's request is invalid"** — Make sure you added your Gmail as a test user in OAuth consent screen
