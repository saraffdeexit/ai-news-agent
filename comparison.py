"""
comparison.py (V2+)

Compares today's assessment with yesterday's assessment.
Identifies what changed and asks Claude to evaluate significance.

This is the "watchdog" layer — it answers: "Is this change worth alerting about?"

Returns:
{
  "has_previous": bool,
  "changes": {
    "new_bottlenecks": [...],
    "resolved_bottlenecks": [...],
    "shifted_themes": [...],
    "takeaway_changed": bool,
  },
  "significance_score": 0-100,  # Claude's assessment
  "significance_reason": "...",  # Why it matters
  "is_significant": bool,  # True if score >= 60
}
"""

import json
import os
from datetime import datetime

import anthropic

from assessment_storage import load_assessment, load_previous_assessment


COMPARISON_MODEL = "claude-opus-4-1-20250805"

SIGNIFICANCE_SYSTEM = """You are evaluating whether changes in AI industry weekly assessments \
are significant enough to alert a busy executive. You have two assessments (yesterday's and today's) \
and a diff of what changed.

Significance = does this change represent a NEW, MATERIAL development that wasn't tracked before?

High significance (70-100):
- New critical bottleneck emerges (e.g., power supply, talent shortage worsens)
- Major pivot in a key theme (e.g., regulation tightens unexpectedly)
- Completely new theme (e.g., security breaches, unexpected startup)
- Takeaway changed to something more urgent/risky

Medium significance (40-70):
- Existing bottleneck worsens (more articles, higher prominence)
- Existing theme shifts focus (e.g., GPU shortage → training cost implications)
- New article on old issue (adds detail but not new pattern)

Low significance (0-40):
- Theme order changed but content same
- Minor wording updates
- Incremental news on stable topic (e.g., one more funding round)
- Takeaway rephrased but message unchanged

Be strict. Busy readers only want alerts for genuine new developments, not noise."""


def _format_bottleneck(b: dict) -> str:
    return f"- {b.get('issue', '')}: {b.get('summary', '')}"


def _format_theme(t: dict) -> str:
    return f"- {t.get('theme', '')}: {t.get('summary', '')}"


def compare_assessments(today: dict, yesterday: dict | None) -> dict:
    """
    Compare today's assessment with yesterday's.
    Returns a change summary and significance score.
    """
    if yesterday is None:
        return {
            "has_previous": False,
            "changes": {"new_bottlenecks": [], "resolved_bottlenecks": [], "shifted_themes": [], "takeaway_changed": False},
            "significance_score": 0,
            "significance_reason": "No previous assessment to compare (first run).",
            "is_significant": False,
        }

    # Extract keys from assessments for comparison
    today_bottleneck_issues = {b.get("issue", "").lower() for b in today.get("bottlenecks", [])}
    yesterday_bottleneck_issues = {b.get("issue", "").lower() for b in yesterday.get("bottlenecks", [])}

    today_themes = {t.get("theme", "").lower() for t in today.get("themes", [])}
    yesterday_themes = {t.get("theme", "").lower() for t in yesterday.get("themes", [])}

    new_bottlenecks = [b for b in today.get("bottlenecks", []) if b.get("issue", "").lower() not in yesterday_bottleneck_issues]
    resolved_bottlenecks = [b for b in yesterday.get("bottlenecks", []) if b.get("issue", "").lower() not in today_bottleneck_issues]
    shifted_themes = list(today_themes - yesterday_themes)
    takeaway_changed = (
        today.get("one_line_takeaway", "").lower().strip()
        != yesterday.get("one_line_takeaway", "").lower().strip()
    )

    changes = {
        "new_bottlenecks": new_bottlenecks,
        "resolved_bottlenecks": resolved_bottlenecks,
        "shifted_themes": shifted_themes,
        "takeaway_changed": takeaway_changed,
    }

    # Format for Claude
    change_summary = f"""
YESTERDAY'S ASSESSMENT ({yesterday.get('date', 'unknown')}):
Takeaway: {yesterday.get('one_line_takeaway', '')}
Bottlenecks:
{chr(10).join(_format_bottleneck(b) for b in yesterday.get('bottlenecks', []))}
Themes:
{chr(10).join(_format_theme(t) for t in yesterday.get('themes', []))}

TODAY'S ASSESSMENT ({today.get('date', 'unknown')}):
Takeaway: {today.get('one_line_takeaway', '')}
Bottlenecks:
{chr(10).join(_format_bottleneck(b) for b in today.get('bottlenecks', []))}
Themes:
{chr(10).join(_format_theme(t) for t in today.get('themes', []))}

CHANGES DETECTED:
- New bottlenecks: {len(new_bottlenecks)} ({', '.join(b.get('issue', '') for b in new_bottlenecks[:3])} {'...' if len(new_bottlenecks) > 3 else ''})
- Resolved bottlenecks: {len(resolved_bottlenecks)}
- New themes: {len(shifted_themes)} ({', '.join(shifted_themes[:3])} {'...' if len(shifted_themes) > 3 else ''})
- Takeaway changed: {takeaway_changed}
"""

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    message = client.messages.create(
        model=COMPARISON_MODEL,
        max_tokens=1000,
        system=SIGNIFICANCE_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": f"Evaluate the significance of these changes:\n{change_summary}\n\nRespond with:\nSIGNIFICANCE_SCORE: <0-100>\nREASON: <1-2 sentences explaining why this score>",
            }
        ],
    )

    response_text = message.content[0].text if message.content else ""

    # Parse Claude's response
    score = 50  # default
    reason = "Could not parse significance assessment."

    lines = response_text.split("\n")
    for line in lines:
        if "SIGNIFICANCE_SCORE:" in line:
            try:
                score_str = line.split("SIGNIFICANCE_SCORE:")[-1].strip().split()[0]
                score = int(score_str)
                score = max(0, min(100, score))
            except (ValueError, IndexError):
                pass
        elif "REASON:" in line:
            reason = line.split("REASON:")[-1].strip()

    return {
        "has_previous": True,
        "changes": changes,
        "significance_score": score,
        "significance_reason": reason,
        "is_significant": score >= 60,
    }


def load_and_compare() -> dict:
    """
    Convenience wrapper: load today and yesterday, compare, return result.
    """
    today = load_assessment()
    yesterday = load_previous_assessment()

    if today is None:
        return {
            "has_previous": False,
            "changes": {},
            "significance_score": 0,
            "significance_reason": "No today assessment found.",
            "is_significant": False,
        }

    return compare_assessments(today, yesterday)


if __name__ == "__main__":
    # Test comparison
    result = load_and_compare()
    print(json.dumps(result, indent=2))
