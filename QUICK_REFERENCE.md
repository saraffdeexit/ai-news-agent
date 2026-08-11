# Quick Reference: Running V1→V4

## Common Commands

### Run Full V1→V4 Pipeline
```bash
python main.py
```
- Fetches news → Summarizes → Assesses → Compares → Investigates (if significant)
- Only sends email if change is significant
- Stores assessment in memory

### Force Send (for Testing)
```bash
python main.py --force
```
- Runs full pipeline and sends email regardless of significance
- Useful for testing email template

### Verbose Output
```bash
python main.py --verbose
```
- Print debug info at each stage
- See Claude's reasoning for significance/investigation

### View Assessment History
```bash
python memory.py
```
or
```python
from memory import print_history_summary
print_history_summary()
```

### Run V1 Only (Original Digest)
```python
from fetch_news import fetch_articles
from summarize import summarize_articles
from send_email import send_digest

articles = fetch_articles()
digest = summarize_articles(articles)
send_digest(digest)  # Always sends
```

---

## Data Flow at a Glance

```
main.py
  ├─ fetch_news.py → articles
  ├─ summarize.py → digest (themes, bottlenecks, takeaway)
  ├─ assessment.py → assessment (normalized state)
  ├─ memory.get_latest() → last_week_assessment
  ├─ compare.py → significance (is_significant, change_type, confidence)
  │
  ├─ IF is_significant:
  │   ├─ investigate.py → investigation (findings, evidence, actions)
  │   └─ send_email_v4.py → alert email (with investigation)
  │
  ├─ memory.save() → assessments.json
  └─ Done
```

---

## File Purposes (TL;DR)

| File | Purpose | V |
|---|---|---|
| `fetch_news.py` | Google News RSS scraper | 1 |
| `summarize.py` | Claude digest generation | 1 |
| `send_email.py` | Simple digest email | 1 |
| `assessment.py` | Normalize digest into comparable state | 2 |
| `memory.py` | Store/load assessment history | 2 |
| `compare.py` | Detect significant changes | 3 |
| `send_email_v4.py` | Alert email with investigation | 3/4 |
| `investigate.py` | Autonomous investigation & validation | 4 |
| `main.py` | Orchestrate entire V1→V4 pipeline | 1–4 |

---

## Environment Variables

Required:
```
ANTHROPIC_API_KEY       # Claude API key
GMAIL_ADDRESS           # Sending Gmail address
GMAIL_APP_PASSWORD      # Gmail 16-char app password
DIGEST_RECIPIENT        # Where to send alerts (can be same as GMAIL_ADDRESS)
```

Set locally:
```bash
export ANTHROPIC_API_KEY="sk-..."
export GMAIL_ADDRESS="your@gmail.com"
export GMAIL_APP_PASSWORD="abcd efgh ijkl mnop"  # 16 chars
export DIGEST_RECIPIENT="you@gmail.com"
```

Set in GitHub Actions (Settings → Secrets → Actions):
```
ANTHROPIC_API_KEY
GMAIL_ADDRESS
GMAIL_APP_PASSWORD
DIGEST_RECIPIENT
```

---

## Tuning Knobs

### Sensitivity (V3)
Edit `compare.py` → `SIGNIFICANCE_PROMPT`:
- Lower confidence threshold → more alerts
- Mention specific domains you care about (e.g. "treasury cares about power costs")

### Investigation Depth (V4)
Edit `investigate.py` → `_build_search_queries()`:
- Add custom queries for your priorities
- Add real web search APIs instead of simulated search

### Alert Style (V3/V4)
Edit `send_email_v4.py` → `render_alert_html()`:
- Change colors, layout, sections
- Add/remove fields

---

## Troubleshooting

| Issue | Fix |
|---|---|
| `ModuleNotFoundError: anthropic` | `pip install anthropic` |
| Gmail auth fails | Check app password is 16 chars, no spaces: `echo $GMAIL_APP_PASSWORD \| wc -c` |
| Claude API errors | Verify `ANTHROPIC_API_KEY` is set: `echo $ANTHROPIC_API_KEY` |
| No email received | Check `DIGEST_RECIPIENT` is valid |
| Assessment not storing | Check `assessments.json` exists: `ls -la assessments.json` |
| Nothing flagged as significant | Tune SIGNIFICANCE_PROMPT in `compare.py` or add `--force` to test |

---

## Sample Week-by-Week Output

### Week 1 (First Run)
```
[1/5] Fetching news...
  Fetched 42 articles
[2/5] Summarizing with Claude...
  Themes: 4, Bottlenecks: 2
[3/5] Building assessment...
  Bottleneck topics: ['gpu_shortage', 'power_constraints']
  Sentiment: bearish
[4/5] Comparing to last week's assessment...
  No prior assessment — treating as first run
  Significant: False (first baseline)
[5/5] Skipping investigation (change not significant)
[MEMORY] Storing assessment...
— NO ALERT (changes not significant)
```

### Week 2 (Stable)
```
[4/5] Comparing to last week's assessment...
  Last week bottlenecks: ['gpu_shortage', 'power_constraints']
  Significant: False (same topics, stable sentiment)
— NO ALERT (changes not significant)
```

### Week 3 (Change Detected!)
```
[4/5] Comparing to last week's assessment...
  Last week bottlenecks: ['gpu_shortage']
  Significant: True ✓
  Change type: escalation
  Confidence: 0.85
[5/5] Launching autonomous investigation...
  Generated 5 search queries
  Investigation confidence: 0.90
  Recommended actions: 3
==============================
✓ SENDING EMAIL ALERT
✓ Alert sent to you@gmail.com
  Subject: [WATCHDOG] Escalation 🔴
  Confidence: 85%
```

---

## Advanced: Accessing Assessment Data Programmatically

```python
from memory import load_history

history = load_history()

# Latest assessment
latest = history[-1]
print(latest['assessment']['sentiment'])  # "bearish"

# Trend over time
for entry in history:
    print(f"{entry['date'][:10]}: {entry['assessment']['sentiment']}")

# Find alerts that were sent
for entry in history:
    if entry.get('significance', {}).get('is_significant'):
        print(f"Alert: {entry['significance']['change_type']}")
```

---

## GitHub Actions: Manual Trigger

In your repo, go to **Actions** tab:
1. Click **"Weekly AI News Digest"** workflow
2. Click **"Run workflow"** button
3. Select branch (`main`) and click **"Run workflow"**

Runs immediately (useful for testing changes).

---

## Next Steps

1. ✓ Set up V1 (you have this)
2. → Add V2 files (`memory.py`, `assessment.py`)
3. → Add V3 files (`compare.py`)
4. → Add V4 files (`investigate.py`, `send_email_v4.py`)
5. → Update `main.py`
6. → Test: `python main.py --verbose`
7. → Deploy to GitHub Actions

See **INTEGRATION_GUIDE.md** for step-by-step instructions.

---

## Questions?

- **Why no alert this week?** → Check `memory.json` + run `main.py --verbose`
- **How do I tune sensitivity?** → Edit `compare.py` SIGNIFICANCE_PROMPT
- **Can I use real web search?** → Yes, update `investigate.py` to use Search API
- **What if watchdog is too aggressive?** → Lower confidence threshold in `main.py`

Good luck! 🚨
