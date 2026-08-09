# ai-news-agent

Weekly AI development news digest. Pulls headlines from Google News RSS,
summarizes them with Claude into themes plus a dedicated **Bottlenecks &
Constraints** section, and emails the result via Gmail. Runs on a
GitHub Actions schedule — same pattern as the Fred-Agent (S&P 500) repo.

## How it works

1. `fetch_news.py` — queries Google News RSS across ~8 rotating AI topics
   (chip supply, compute bottlenecks, power/energy, regulation, model
   releases, funding, talent) and dedupes results from the last 7 days.
2. `summarize.py` — sends the headlines to Claude, which groups them into
   themes and pulls out a bottlenecks section, returned as structured JSON.
3. `send_email.py` — renders that JSON into an HTML email and sends it via
   Gmail SMTP.
4. `main.py` — runs the three steps in order.
5. `.github/workflows/weekly.yml` — runs `main.py` every Monday, plus a
   manual "Run workflow" button in the Actions tab.

## Setup

### 1. Create the repo
Push this folder to a new GitHub repo, e.g. `ai-news-agent`.

### 2. Gmail app password
Same as Fred-Agent: enable 2-Step Verification on the sending Gmail
account, then create an **App Password** at
myaccount.google.com/apppasswords. Use that (not your normal password).

### 3. Anthropic API key
Get one at console.anthropic.com if you don't already have one from
Fred-Agent (a fresh key is cleaner so usage is tracked separately).

### 4. Add repo secrets
In the repo: **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Value |
|---|---|
| `ANTHROPIC_API_KEY` | your Claude API key |
| `GMAIL_ADDRESS` | the sending Gmail address |
| `GMAIL_APP_PASSWORD` | the 16-character app password |
| `DIGEST_RECIPIENT` | where the digest should land (can be the same address) |

### 5. Test it
Go to the **Actions** tab → "Weekly AI News Digest" → **Run workflow**
to trigger it manually before waiting for Monday.

### Running locally
```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...
export GMAIL_ADDRESS=...
export GMAIL_APP_PASSWORD=...
export DIGEST_RECIPIENT=...
python main.py
```

## Tuning

- **Queries**: edit the `QUERIES` list in `fetch_news.py` to shift topic
  coverage (e.g. add "AI in healthcare" or narrow to just infra topics).
- **Schedule**: edit the `cron` line in `.github/workflows/weekly.yml`.
  Cron is UTC — the default (`0 13 * * 1`) is Monday ~8am Central.
- **Summary style**: edit `SYSTEM_PROMPT` in `summarize.py` to change
  tone, section structure, or how aggressively it flags bottlenecks.
# ai-news-agent
