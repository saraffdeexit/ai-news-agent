# AI News Watchdog — V1 → V4 Architecture Guide

## Overview

This is the progression from a simple **weekly digest** (V1) to an intelligent **autonomous watchdog** (V4) that only alerts you when something genuinely matters.

```
V1: News → Summarize → Email (always send)
V2: ... → Store Assessment + History
V3: ... → Compare Assessments → Significance Check → Conditional Send
V4: ... → Auto-Investigate → Send Rich Alert (with investigation findings)
```

---

## The Five Layers

### **V1: Weekly Digest (Original)**
- `fetch_news.py` → `summarize.py` → `send_email.py`
- **Output**: HTML email with themes + bottlenecks every Monday
- **Storage**: None (no history)

### **V2: Memory** ⭐ New
- Introduced: `memory.py`, `assessment.py`
- **Adds**: Persistent storage of assessments + full digest history
- **Structure**: Each week's entry = digest + normalized "assessment"
- **Assessment** = bottleneck topics + themes + priority areas + sentiment
- **Purpose**: Enable week-to-week comparison

```json
{
  "date": "2025-08-10T15:30:00Z",
  "digest": { /* full themes, bottlenecks, takeaway */ },
  "assessment": {
    "bottleneck_topics": ["gpu_shortage", "power_constraints"],
    "themes": ["Compute", "Infrastructure"],
    "priority_areas": ["compute_capacity", "power_energy"],
    "sentiment": "bearish"
  }
}
```

### **V3: Watchdog** ⭐ New
- Introduced: `compare.py`
- **Adds**: Significance classification via Claude
- **Decision**: "Did something materially change this week?"
- **Triggers**: Only send email if `is_significant == True`
- **Avoids**: Alert fatigue from noise week-to-week
- **Scoring**: Claude evaluates change_type (new_issue, escalation, new_theme, resolved, sentiment_shift)

```json
{
  "is_significant": true,
  "change_type": "escalation",
  "key_changes": ["GPU shortage escalated to critical"],
  "confidence": 0.85,
  "reasoning": "Sentiment shifted from neutral to bearish"
}
```

### **V4: Autonomous Investigation** ⭐ New (The Interesting Part)
- Introduced: `investigate.py`
- **Triggered**: When `significance.is_significant == True`
- **Behavior**: Automatically searches for corroborating evidence before sending alert
- **Output**: Investigation findings + recommended actions
- **Confidence Scoring**: Validates the significance with evidence

```json
{
  "triggered": true,
  "finding": "NVIDIA earnings call confirmed H100 supply constrained through Q2 2025",
  "supporting_evidence": [
    "NVIDIA Q1 2025 earnings — limited supply guidance",
    "Taiwan fab delays due to power constraints",
    "Cloud provider waiting lists > 6 months"
  ],
  "confidence": 0.90,
  "recommended_actions": [
    "Monitor NVIDIA next earnings for supply updates",
    "Track fab capacity announcements",
    "Watch for alternative GPU adoption"
  ]
}
```

### **V5 (Future): Trend Detection**
- Look for patterns across months of assessments
- Detect regime shifts (e.g. "shortage era → abundance era")
- Multi-signal alerts (correlated changes across bottlenecks)

---

## Data Flow

```
Fetch News (7 days)
    ↓
    [Deduplicated article list]
    ↓
Summarize with Claude (tool-call → structured JSON)
    ↓
    [digest: themes, bottlenecks, takeaway]
    ↓
Extract Assessment (normalize digest into comparable state)
    ↓
    [assessment: bottleneck_topics, themes, priority_areas, sentiment]
    ↓
Load Previous Assessment from Memory
    ↓
Compare & Evaluate Significance (Claude scoring)
    ↓
    [significance: is_significant, change_type, confidence]
    ↓
    IF is_significant:
        ├─→ Investigate (gather evidence, validate)
        │   ↓
        │   [investigation: findings, evidence, actions, confidence]
        │
        └─→ Send Alert Email (with investigation findings)
    ELSE:
        └─→ Store assessment, do not send email
    
    ↓
Save to Memory (digest + assessment + significance + investigation)
```

---

## Key Files

### Core Pipeline
- **`fetch_news.py`** — Google News RSS (unchanged from V1)
- **`summarize.py`** — Claude tool-call digest (unchanged from V1)
- **`send_email.py`** — Original digest email (unchanged from V1)

### V2+ Additions
- **`memory.py`** — Persistent assessment history (JSON file)
- **`assessment.py`** — Convert digest → comparable state
- **`compare.py`** — Detect significance via Claude
- **`investigate.py`** — Auto-search for evidence (V4)
- **`send_email_v4.py`** — Alert email with investigation (V3+)
- **`main.py`** — Orchestrates full V1→V4 pipeline

---

## How to Run

### Local Testing

```bash
# Test V1 (original digest)
python -c "from fetch_news import fetch_articles; from summarize import summarize_articles; digest = summarize_articles(fetch_articles()); print(digest)"

# Test V1→V4 full pipeline (will store assessment but not email)
python main.py --verbose

# Test V1→V4 full pipeline + send email (for testing, forces email)
python main.py --force

# View stored assessment history
python -c "from memory import print_history_summary; print_history_summary()"
```

### GitHub Actions (Weekly)

Update `.github/workflows/weekly.yml`:

```yaml
- name: Run AI News Watchdog v1→v4
  run: |
    pip install -r requirements.txt
    python main.py
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
    GMAIL_ADDRESS: ${{ secrets.GMAIL_ADDRESS }}
    GMAIL_APP_PASSWORD: ${{ secrets.GMAIL_APP_PASSWORD }}
    DIGEST_RECIPIENT: ${{ secrets.DIGEST_RECIPIENT }}
```

---

## Configuration & Tuning

### What Counts as "Significant"?

Edit the system prompts in:
- **`compare.py`** — SIGNIFICANCE_PROMPT
- **`investigate.py`** — INVESTIGATION_PROMPT

Example: For a treasury role (your case), "significant" might emphasize:
- Infrastructure cost implications
- Supply chain shocks
- Regulatory friction
- Funding/talent dynamics

### Memory Storage

Assessment history is stored in `assessments.json` (auto-created):

```json
{
  "assessments": [
    { "date": "...", "digest": {...}, "assessment": {...}, "significance": {...} },
    { "date": "...", "digest": {...}, "assessment": {...}, "significance": {...} }
  ]
}
```

To **archive** old assessments:
```bash
# Backup and trim to last 12 weeks
cp assessments.json assessments.backup.json
python -c "import json; data = json.load(open('assessments.json')); data['assessments'] = data['assessments'][-12:]; json.dump(data, open('assessments.json', 'w'), indent=2)"
```

### Investigation Depth

In `investigate.py`, the `_build_search_queries()` function generates targeted searches. You can:
1. **Add custom queries** for domains you care about (e.g. specific companies)
2. **Integrate real web search** (replace the simulated search with API calls to Google Search, Bing, etc.)
3. **Add custom data sources** (regulatory filings, earnings calendars, Twitter API, etc.)

---

## Design Decisions

### Why Claude for Significance Scoring?

- **Nuance**: "New topic in news" ≠ "significant shift in industry state"
- **Context**: Claude understands that GPU shortage #47 might be noise, but "power constraints halting fabs" is structural
- **Cost**: Haiku + cached prompts = cheap significance checks

### Why Separate "Assessment" from Digest?

- **Digest** is detailed, human-readable (all articles, full context)
- **Assessment** is normalized, machine-comparable (topics, sentiment, areas)
- Allows comparison without full text similarity (which fails when language shifts)

### Why Investigate Before Sending?

- **Reduces false alarms**: Validates the detected change with corroborating evidence
- **Adds intelligence**: Alert includes "why this matters" + "what to watch next"
- **Confidence scoring**: Tells you how confident the watchdog is in the alert

### Why JSON File Storage (not Database)?

- **Simplicity**: Works in GitHub Actions without extra deps
- **Transparency**: History is human-readable, version-controllable
- **Scalability**: 52 weeks × ~2KB per assessment = 100KB/year (fine for Git)
- **Future**: Trivial to migrate to Postgres/DynamoDB later

---

## What's Next (Future Enhancements)

### V4.5: Real Web Search
```python
# In investigate.py, replace simulated search with:
from googleapiclient.discovery import build
results = search_service.cse().list(q=query, cx=cse_id).execute()
```

### V5: Trend Detection
```python
# Detect multi-week patterns
def detect_trends(assessments):
    # "GPU shortage steadily worsening for 4 weeks"
    # "New regulation emerging across 3 separate themes"
    # "Funding activity spike — 7 new rounds in 2 weeks"
    pass
```

### V5.5: Custom Watches
```python
# Alert when specific company/topic changes
# E.g. "Email me if NVIDIA news escalates"
# E.g. "Alert if power constraint severity > threshold"
```

### V6: Correlated Signals
```python
# When significance detected, check if related signals are also rising
# E.g. GPU shortage + talent hiring surge + funding rounds → sector expansion
```

---

## Testing Checklist

- [ ] `python main.py --verbose` runs end-to-end
- [ ] Memory file created with first assessment
- [ ] Second run compares to first assessment
- [ ] Significance scoring works (shows is_significant + change_type)
- [ ] `python main.py --force` sends test email
- [ ] Email includes alert + investigation findings if triggered
- [ ] GitHub Actions workflow triggers on schedule
- [ ] Email lands in inbox with correct subject line

---

## Troubleshooting

### Memory file not creating
```python
from memory import _ensure_file
_ensure_file()
```

### No API responses
```bash
echo $ANTHROPIC_API_KEY  # verify secret is set
python -c "import anthropic; print(anthropic.__version__)"
```

### Investigation not triggered
Check `compare.py` output — is `significance.is_significant == True`? If not, the change wasn't classified as significant. Adjust SIGNIFICANCE_PROMPT or lower confidence threshold.

### Email not sending
Verify Gmail app password:
```bash
# Should be 16 alphanumeric chars, no spaces
echo $GMAIL_APP_PASSWORD | wc -c
```

---

## Questions?

This is a sophisticated system. If you hit rough edges:
1. Run with `--verbose` to see decision points
2. Check `memory.json` for what's stored
3. Review Claude's tool inputs in the logs
4. Adjust prompts in `compare.py` / `investigate.py`

The goal: **Alert only when something genuinely matters. Investigate automatically before crying wolf.**
