# Integration Guide: V1 → V4 Upgrade

You already have V1 working. Here's how to layer in V2–V4 with zero breaking changes.

---

## Phase 1: Add V2 Files (Memory Layer) — 10 mins

Copy these new files to your repo:
- `memory.py`
- `assessment.py`

Update `requirements.txt`:
```
anthropic>=0.21.0
feedparser>=6.0.10
```

Test locally:
```bash
pip install -r requirements.txt

# Run V1 + V2: fetch, summarize, extract assessment, store
python -c "
from fetch_news import fetch_articles
from summarize import summarize_articles
from assessment import build_assessment
from memory import save_assessment

articles = fetch_articles()
digest = summarize_articles(articles)
assessment = build_assessment(digest)
save_assessment(digest, assessment)

print('✓ Assessment stored in assessments.json')
"
```

Verify `assessments.json` exists with your first entry.

---

## Phase 2: Add V3 (Watchdog Layer) — 10 mins

Copy this new file:
- `compare.py`

Update `main.py` (or create a new `main_v3.py` to run alongside V1):

```python
from fetch_news import fetch_articles
from summarize import summarize_articles
from assessment import build_assessment
from compare import evaluate_significance
from memory import save_assessment, get_latest_assessment

articles = fetch_articles()
digest = summarize_articles(articles)
assessment = build_assessment(digest)

# NEW: Compare to last week
prev = get_latest_assessment()
last_assessment = prev.get("assessment") if prev else None
significance = evaluate_significance(assessment, last_assessment)

# NEW: Store assessment + significance
save_assessment(digest, assessment, significance=significance)

# NEW: Only send if significant
if significance.get("is_significant"):
    from send_email import send_digest
    send_digest(digest)
    print(f"✓ Alert sent (change type: {significance.get('change_type')})")
else:
    print("— No alert (change not significant)")
```

Test:
```bash
python main_v3.py  # First run: no prior data, may not be significant
python main_v3.py  # Second run: compare to first, detect change/stability
```

---

## Phase 3: Add V4 (Autonomous Investigation) — 15 mins

Copy these files:
- `investigate.py`
- `send_email_v4.py`

Use the full `main.py` provided:

```bash
python main.py
```

This orchestrates: fetch → summarize → assess → compare → investigate → send.

Test the investigation:
```bash
python main.py --verbose  # See investigation in action
```

Look for output like:
```
[investigate] Significant change detected, launching investigation...
[investigate] Generated 5 search queries: [...]
[investigate] Investigation complete: end_turn
[investigate] Confidence: 0.90, Actions: 3
```

---

## Phase 4: Update GitHub Actions

Your current `.github/workflows/weekly.yml` looks like:

```yaml
name: Weekly AI News Digest

on:
  schedule:
    - cron: '0 13 * * 1'  # Monday 8am Central
  workflow_dispatch:

jobs:
  digest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - run: pip install -r requirements.txt
      - run: python main.py
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GMAIL_ADDRESS: ${{ secrets.GMAIL_ADDRESS }}
          GMAIL_APP_PASSWORD: ${{ secrets.GMAIL_APP_PASSWORD }}
          DIGEST_RECIPIENT: ${{ secrets.DIGEST_RECIPIENT }}
```

**No changes needed!** `main.py` handles V1–V4 automatically. The job will:
1. Run the full pipeline
2. Store assessment in memory
3. Only send email if significant

### Optional: Commit Assessment History

To keep assessment history in the repo (version control your watchdog decisions):

```yaml
- run: python main.py
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
    GMAIL_ADDRESS: ${{ secrets.GMAIL_ADDRESS }}
    GMAIL_APP_PASSWORD: ${{ secrets.GMAIL_APP_PASSWORD }}
    DIGEST_RECIPIENT: ${{ secrets.DIGEST_RECIPIENT }}

- name: Commit assessment history
  run: |
    git config user.name "AI Watchdog"
    git config user.email "watchdog@ai-news-agent"
    git add assessments.json
    git commit -m "Add weekly assessment" || true
    git push origin main
```

This creates a Git history of your alerts + assessments (useful for auditing, trend analysis).

---

## Phase 5: Tune for Your Use Case

### As a Treasury Exec

You care about:
- **Infrastructure costs** (power constraints, fab delays)
- **Supply shocks** (chip shortages, talent exodus)
- **Regulatory friction** (impacts deployment timelines, capex)

Edit `compare.py` SIGNIFICANCE_PROMPT:

```python
SIGNIFICANCE_PROMPT = """You are evaluating AI industry changes relevant to infrastructure costs and supply chain stability.

Significant changes for treasury perspective:
1. New supply bottlenecks (GPU, power, talent) — these impact capex
2. Cost escalations (power prices, compute costs increasing)
3. Regulatory friction that delays capex deployment
4. Funding/valuation swings (affect competitor CapEx budgets)
5. Talent dynamics (hiring freezes or surges indicate sector health)

Is there something that would materially affect infrastructure planning timelines or capex budgets?
"""
```

### As a Startup Founder

You care about:
- **Model capabilities** (new APIs, open-source releases)
- **Funding dynamics** (Series raises, M&A)
- **Emerging competitors** (new models, new platforms)

Edit `assessment.py` priority_areas logic:

```python
if any(w in combined for w in ["funding", "round", "acquisition", "valuation"]):
    priority_areas.append("competitive_funding")

if any(w in combined for w in ["open source", "hugging face", "mistral"]):
    priority_areas.append("open_source_models")
```

---

## Phase 6: Validate the Full Loop

Run through a complete cycle:

```bash
# Week 1: First run
python main.py --force  # --force sends email for testing
# → Creates assessments.json, sends digest

# Week 2: Run again
python main.py  # should NOT send (no significant change)
# → Compares to week 1, likely "no alert" unless news drastically shifted

# Week 3: Run with mock change
# Manually edit assessments.json to make week 2 assessment different
python main.py  # should send alert
# → Detects change, investigates, sends watchdog alert
```

---

## Breaking Changes: None

Your existing setup:
- ✓ `fetch_news.py` — unchanged
- ✓ `summarize.py` — unchanged
- ✓ `send_email.py` — unchanged (kept for reference)
- ✓ GitHub Actions workflow — unchanged (just calls `main.py` instead)
- ✓ Secrets — unchanged (same env vars)

You're adding:
- + New files (`memory.py`, `assessment.py`, `compare.py`, `investigate.py`, `send_email_v4.py`, `main.py`)
- + `assessments.json` (in `.gitignore` or committed, your choice)

**Migration Path**: 
- Today: run V1 every Monday, get digest email
- After Phase 1: run V1+V2, get digest + store assessment
- After Phase 3: run V1–V4, only get email when something significant changes

---

## File Checklist

After integration, your repo should have:

```
ai-news-agent/
├── fetch_news.py          (V1, unchanged)
├── summarize.py           (V1, unchanged)
├── send_email.py          (V1, unchanged, now mostly unused)
├── main.py                (NEW: V1→V4 orchestrator)
│
├── memory.py              (NEW: V2 storage)
├── assessment.py          (NEW: V2 normalization)
├── compare.py             (NEW: V3 significance)
├── investigate.py         (NEW: V4 investigation)
├── send_email_v4.py       (NEW: V3/V4 alert email)
│
├── V4_ARCHITECTURE.md     (NEW: design guide)
├── INTEGRATION_GUIDE.md   (NEW: this file)
├── README.md              (existing, update intro)
├── requirements.txt       (unchanged, already has deps)
│
├── assessments.json       (AUTO-CREATED: assessment history)
├── .github/workflows/weekly.yml  (unchanged or updated for auto-commit)
└── .gitignore             (add: assessments.json if not versioning)
```

---

## Rollback Plan

If V4 is too aggressive/noisy:

**Option A: Disable Investigation**
```python
# In main.py, comment out investigate()
# investigation = investigate(significance, digest, articles)
investigation = None
```

**Option B: Raise Significance Threshold**
```python
# In main.py, before sending:
if significance.get("confidence", 0) > 0.75:  # was 0.5+
    send_alert(...)
```

**Option C: Revert to V1**
```python
# In main.py, replace with:
from send_email import send_digest
send_digest(digest)  # always send, ignore significance
```

---

## Success Criteria

- [ ] `python main.py` runs without errors
- [ ] First run creates `assessments.json`
- [ ] Second run compares assessments
- [ ] Significant change triggers investigation + email
- [ ] Email includes investigation findings
- [ ] GitHub Actions runs on schedule
- [ ] You get fewer, higher-quality alerts

---

## Next: Custom Tuning

Once this is live:

1. **Week 1–2**: Observe what gets flagged as "significant". Is the watchdog too sensitive or too quiet?
2. **Adjust prompts**: Edit `SIGNIFICANCE_PROMPT` and `INVESTIGATION_PROMPT` to match your priorities
3. **Add investigations**: Extend `_build_search_queries()` with company-specific searches
4. **Track trends**: Review `assessments.json` after 4 weeks to see patterns

That's it. You now have an intelligent, autonomous watchdog. 🚨
