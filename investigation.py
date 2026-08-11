"""
investigation.py (V4+)

When V3 detects a significant change, V4 automatically searches for
supporting evidence. This is the "watchdog with a nose for details."

Strategy:
1. Extract keywords from the new/changed bottlenecks and themes
2. Perform targeted web searches
3. Summarize findings with Claude
4. Return a brief investigation report

This prevents false alarms ("is this really significant?") and provides
context ("here's what else is happening around this").
"""

import json
import os
from datetime import datetime, timedelta

import anthropic

INVESTIGATION_MODEL = "claude-opus-4-1-20250805"

INVESTIGATION_SYSTEM = """You are a research assistant investigating emerging trends in AI \
development. You will be given search results and asked to synthesize them into a brief summary.

Your job: confirm whether these search results support the significance of a detected change, \
and highlight any additional context that's important.

Be concise. Focus on facts that either:
1. Confirm the change is real and material
2. Add important context the digest didn't capture
3. Reveal cascading impacts

If search results DON'T support the detected change, say so clearly."""


def _extract_keywords(changes: dict) -> list[str]:
    """
    Extract search keywords from detected changes.
    Prioritize new bottlenecks and new themes.
    """
    keywords = []

    # New bottlenecks are highest priority
    for bottleneck in changes.get("new_bottlenecks", []):
        issue = bottleneck.get("issue", "").strip()
        if issue:
            keywords.append(issue)

    # New themes
    for theme in changes.get("shifted_themes", []):
        if theme:
            keywords.append(theme)

    return keywords[:3]  # Top 3 to avoid too many searches


def investigate_changes(changes: dict, significance_score: int) -> dict:
    """
    If significant change detected, perform targeted searches.
    
    Returns:
    {
      "investigated": bool,
      "searches_performed": [
        {
          "query": "...",
          "findings": "...",
        }
      ],
      "investigation_summary": "...",
      "confidence_uplift": 0-30,  # Does investigation raise confidence in the alert?
    }
    """
    
    if significance_score < 60:
        # Not significant, no need to investigate
        return {
            "investigated": False,
            "searches_performed": [],
            "investigation_summary": "Below significance threshold; no investigation needed.",
            "confidence_uplift": 0,
        }

    keywords = _extract_keywords(changes)
    if not keywords:
        return {
            "investigated": False,
            "searches_performed": [],
            "investigation_summary": "No specific keywords extracted for investigation.",
            "confidence_uplift": 0,
        }

    # Perform searches
    searches = []
    for keyword in keywords:
        try:
            # In production, you'd call web_search here
            # For now, this is a placeholder that shows the structure
            findings = _search_and_summarize(keyword)
            searches.append({
                "query": keyword,
                "findings": findings,
            })
        except Exception as e:
            print(f"[investigation] Search for '{keyword}' failed: {e}")
            continue

    if not searches:
        return {
            "investigated": False,
            "searches_performed": [],
            "investigation_summary": "Searches failed; unable to investigate.",
            "confidence_uplift": 0,
        }

    # Synthesize findings
    summary = _synthesize_findings(searches, changes)
    confidence_uplift = 10 + len(searches) * 5  # Rough: more evidence = higher confidence

    return {
        "investigated": True,
        "searches_performed": searches,
        "investigation_summary": summary,
        "confidence_uplift": min(30, confidence_uplift),
    }


def _search_and_summarize(keyword: str) -> str:
    """
    Perform a web search for a keyword and summarize results.
    This is where you'd call web_search or a real search API.
    
    Placeholder returns a mock string; in production, integrate with
    web_search tool or httpx-based requests.
    """
    # TODO: Call web_search or your preferred search engine
    # For now, return a placeholder
    return f"[Investigation search for '{keyword}' would happen here in production]"


def _synthesize_findings(searches: list[dict], changes: dict) -> str:
    """
    Use Claude to synthesize search findings into a brief summary.
    """
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    
    search_text = "\n".join(
        f"Search: '{s['query']}'\nFindings: {s['findings']}" for s in searches
    )

    new_bottlenecks = [b.get("issue", "") for b in changes.get("new_bottlenecks", [])]
    new_themes = changes.get("shifted_themes", [])

    prompt = f"""Synthesize these search results to confirm the significance of detected changes.

Changes detected:
- New bottlenecks: {', '.join(new_bottlenecks) or 'none'}
- New themes: {', '.join(new_themes) or 'none'}

Search findings:
{search_text}

In 2-3 sentences, does the evidence support the detected change? Any important context?"""

    message = client.messages.create(
        model=INVESTIGATION_MODEL,
        max_tokens=500,
        system=INVESTIGATION_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text if message.content else "Investigation inconclusive."


if __name__ == "__main__":
    # Test with mock changes
    test_changes = {
        "new_bottlenecks": [
            {"issue": "Power consumption in AI training", "summary": "..."}
        ],
        "resolved_bottlenecks": [],
        "shifted_themes": ["Energy Constraints"],
        "takeaway_changed": True,
    }

    result = investigate_changes(test_changes, significance_score=75)
    print(json.dumps(result, indent=2))
