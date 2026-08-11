"""
main.py (v1→v4)

Orchestrates the full pipeline:
  1. Fetch news from Google News RSS
  2. Summarize with Claude
  3. Extract assessment (normalized state)
  4. Compare to last week's assessment
  5. If significant, investigate autonomously
  6. Send email only if significant (or if force flag)
"""

import sys
import os
import json
from typing import Optional

from fetch_news import fetch_articles
from summarize import summarize_articles
from assessment import build_assessment
from compare import evaluate_significance
from investigate import investigate
from memory import (
    load_history,
    get_latest_assessment,
    save_assessment,
    print_history_summary,
)


def main(force_send: bool = False, verbose: bool = False):
    """
    Run the full V1→V4 pipeline.
    
    Args:
        force_send: if True, send email even if not significant (useful for testing)
        verbose: if True, print debug info
    """
    
    print("\n" + "="*70)
    print("AI NEWS WATCHDOG V4 — Running weekly assessment")
    print("="*70)
    
    # V1: Fetch & Summarize
    print("\n[1/5] Fetching news...")
    articles = fetch_articles()
    print(f"  Fetched {len(articles)} articles")
    
    print("\n[2/5] Summarizing with Claude...")
    digest = summarize_articles(articles)
    print(f"  Themes: {len(digest.get('themes', []))}")
    print(f"  Bottlenecks: {len(digest.get('bottlenecks', []))}")
    
    # V2: Extract Assessment
    print("\n[3/5] Building assessment (normalized state)...")
    this_week_assessment = build_assessment(digest)
    print(f"  Bottleneck topics: {this_week_assessment['bottleneck_topics']}")
    print(f"  Sentiment: {this_week_assessment['sentiment']}")
    print(f"  Priority areas: {this_week_assessment['priority_areas']}")
    
    # V3: Compare & Evaluate Significance
    print("\n[4/5] Comparing to last week's assessment...")
    previous_history = get_latest_assessment()
    last_week_assessment = previous_history.get("assessment") if previous_history else None
    
    if last_week_assessment:
        print(f"  Last week bottlenecks: {last_week_assessment['bottleneck_topics']}")
    else:
        print("  No prior assessment — treating as first run")
    
    significance = evaluate_significance(this_week_assessment, last_week_assessment)
    print(f"  Significant: {significance.get('is_significant')}")
    print(f"  Change type: {significance.get('change_type')}")
    print(f"  Confidence: {significance.get('confidence'):.2f}")
    
    # V4: Investigate if Significant
    investigation = None
    if significance.get("is_significant"):
        print("\n[5/5] Launching autonomous investigation...")
        investigation = investigate(significance, digest, 
                                   [{"title": a.title, "source": a.source} for a in articles])
        print(f"  Investigation confidence: {investigation.get('confidence', 0):.2f}")
        print(f"  Recommended actions: {len(investigation.get('recommended_actions', []))}")
    else:
        print("\n[5/5] Skipping investigation (change not significant)")
        investigation = None
    
    # Store Assessment in Memory (V2+)
    print("\n[MEMORY] Storing assessment...")
    save_assessment(
        digest=digest,
        assessment=this_week_assessment,
        significance=significance,
        investigation=investigation,
    )
    
    # Decision: Send Email?
    should_send = force_send or significance.get("is_significant", False)
    
    if should_send:
        print("\n" + "="*70)
        print("✓ SENDING EMAIL ALERT")
        print("="*70)
        
        # Import and send
        from send_email_v4 import send_alert
        send_alert(
            digest=digest,
            assessment=this_week_assessment,
            significance=significance,
            investigation=investigation,
        )
    else:
        print("\n" + "="*70)
        print("— NO ALERT (changes not significant)")
        print("="*70)
        print("Digest and assessment stored in memory. No email sent.")
    
    # Summary
    print("\n[SUMMARY]")
    print_history_summary()


if __name__ == "__main__":
    force = "--force" in sys.argv
    verbose = "--verbose" in sys.argv
    
    main(force_send=force, verbose=verbose)
