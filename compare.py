"""
compare.py

V3 Watchdog: Compares two assessments and classifies whether changes are significant.

Uses Claude to evaluate: did anything materially change this week that's worth alerting about?

Significant changes might be:
  - New bottleneck emerged (e.g. first time GPU shortage mentioned)
  - Bottleneck escalated (sentiment shifted bearish)
  - Focus area changed (shift in priority_areas)
  - New theme/topic appeared
  - Volatility in sentiment week-to-week
"""

import json
import os
import anthropic


SIGNIFICANCE_PROMPT = """You are evaluating whether AI development news has changed significantly this week.

CRITICAL: Use CANONICAL bottleneck topics for comparison, NOT raw issue names.
The bottleneck_topics field contains canonical forms (e.g., "compute_capacity" instead of 
"GPU Shortage" or "NVIDIA Capacity Crisis"). These are the forms to compare week-to-week.

If bottleneck_topics are identical, the same underlying issues are present — do NOT flag as escalation 
just because the raw wording changed (e.g., "GPU shortage" vs "NVIDIA capacity crisis" = same issue).

You will be given:
- This week's assessment (canonical bottleneck_topics, themes, sentiment, raw bottleneck_issues for context)
- Last week's assessment (if available)

Determine if there's a meaningful shift. Consider:
1. NEW canonical bottleneck topics (topics in this week that weren't in last week)
2. ESCALATING issues (sentiment worsening, issue prominence increasing)
3. NEW focus areas or themes
4. RESOLVED issues (canonical topic disappeared — actually good news, still notable)
5. Dramatic swings in sentiment

DO NOT flag as significant if:
- Same canonical bottleneck topics but different wording (e.g., "GPU shortage" → "NVIDIA capacity crisis")
- Only raw issue names changed while canonical topics stayed the same

Return structured JSON with:
- is_significant: boolean (true if something materially changed)
- reasoning: 1-2 sentence explanation
- change_type: one of ["new_issue", "escalation", "new_theme", "resolved", "sentiment_shift", "none"]
- key_changes: list of specific changes (max 3)
- confidence: 0.0-1.0 confidence in the significance assessment
"""

SIGNIFICANCE_TOOL = {
    "name": "evaluate_significance",
    "description": "Evaluate whether the week's assessment changes are significant.",
    "input_schema": {
        "type": "object",
        "properties": {
            "is_significant": {"type": "boolean"},
            "reasoning": {"type": "string"},
            "change_type": {
                "type": "string",
                "enum": ["new_issue", "escalation", "new_theme", "resolved", "sentiment_shift", "none"]
            },
            "key_changes": {
                "type": "array",
                "items": {"type": "string"},
                "maxItems": 3,
            },
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["is_significant", "reasoning", "change_type", "key_changes", "confidence"],
    },
}


def evaluate_significance(this_week: dict, last_week: Optional[dict] = None) -> dict:
    """
    Use Claude to evaluate if changes between assessments are significant.
    
    Uses CANONICAL bottleneck topics for comparison to avoid false positives from wording changes.
    E.g., "GPU Shortage" and "NVIDIA Capacity Crisis" both map to "compute_capacity" and are
    recognized as the same underlying issue.
    
    Args:
        this_week: assessment from current week
        last_week: assessment from previous week (optional)
    
    Returns:
        significance dict with is_significant, reasoning, change_type, key_changes, confidence
    """
    
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    
    if last_week:
        # Pre-comparison: highlight what changed at the canonical level
        this_topics = set(this_week.get("bottleneck_topics", []))
        last_topics = set(last_week.get("bottleneck_topics", []))
        
        new_topics = this_topics - last_topics
        resolved_topics = last_topics - this_topics
        stable_topics = this_topics & last_topics
        
        pre_analysis = f"""
CANONICAL BOTTLENECK ANALYSIS:
  New issues: {new_topics if new_topics else "none"}
  Resolved issues: {resolved_topics if resolved_topics else "none"}
  Stable issues: {stable_topics if stable_topics else "none"}
  
Raw issue names this week: {this_week.get('bottleneck_issues', [])}
Raw issue names last week: {last_week.get('bottleneck_issues', [])}
"""
        
        comparison_text = f"""
{pre_analysis}

THIS WEEK'S ASSESSMENT:
{json.dumps(this_week, indent=2)}

LAST WEEK'S ASSESSMENT:
{json.dumps(last_week, indent=2)}

NOTE: bottleneck_topics are CANONICAL forms. "GPU Shortage" and "NVIDIA Capacity Crisis" 
both normalize to "compute_capacity". Only alert if the canonical topics actually changed,
not just the raw wording.

Has something materially changed?
"""
    else:
        comparison_text = f"""
THIS WEEK'S ASSESSMENT (no prior data):
{json.dumps(this_week, indent=2)}

This is the first assessment. Is there anything unusual or noteworthy in this week's data?
Note: bottleneck_topics are canonical forms (e.g., "compute_capacity" rather than raw issue names).
"""
    
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1000,
        system=SIGNIFICANCE_PROMPT,
        tools=[SIGNIFICANCE_TOOL],
        tool_choice={"type": "tool", "name": "evaluate_significance"},
        messages=[
            {
                "role": "user",
                "content": comparison_text,
            }
        ],
    )
    
    print(f"[compare] Significance evaluation: {message.stop_reason}")
    
    for block in message.content:
        if block.type == "tool_use" and block.name == "evaluate_significance":
            result = block.input
            print(f"[compare] Significant: {result.get('is_significant')}, "
                  f"Type: {result.get('change_type')}, "
                  f"Confidence: {result.get('confidence')}")
            return result
    
    raise RuntimeError("Claude did not return significance evaluation")


# Type hint helper
from typing import Optional

if __name__ == "__main__":
    # Test 1: Same canonical bottlenecks (no false positive)
    print("=== Test 1: Same Issues, Different Wording (No False Positive) ===")
    this_week_assess = {
        "bottleneck_topics": ["compute_capacity", "power_energy"],  # canonical forms
        "bottleneck_issues": ["GPU Shortage", "Power Constraints"],  # raw forms
        "themes": ["Compute", "Infrastructure"],
        "priority_areas": ["compute_capacity", "power_energy"],
        "sentiment": "bearish",
        "bottleneck_count": 2,
        "theme_count": 2,
        "takeaway_snippet": "GPU shortage worsens",
    }
    
    last_week_assess = {
        "bottleneck_topics": ["compute_capacity", "power_energy"],  # same canonical forms
        "bottleneck_issues": ["NVIDIA Capacity Crisis", "Data Center Power Crisis"],  # different wording
        "themes": ["Infrastructure"],
        "priority_areas": ["compute_capacity", "power_energy"],
        "sentiment": "neutral",
        "bottleneck_count": 2,
        "theme_count": 1,
        "takeaway_snippet": "NVIDIA capacity tight",
    }
    
    sig = evaluate_significance(this_week_assess, last_week_assess)
    print("\nResult:")
    print(json.dumps(sig, indent=2))
    
    # Test 2: Real escalation (canonical topics changed)
    print("\n\n=== Test 2: Real Escalation (New Canonical Topic) ===")
    week2 = {
        "bottleneck_topics": ["compute_capacity", "power_energy"],
        "bottleneck_issues": ["GPU Shortage", "Power Constraints"],
        "themes": ["Compute", "Infrastructure"],
        "priority_areas": ["compute_capacity", "power_energy"],
        "sentiment": "bearish",
        "bottleneck_count": 2,
        "theme_count": 2,
        "takeaway_snippet": "GPU and power both tightening",
    }
    
    week1 = {
        "bottleneck_topics": ["compute_capacity"],  # only GPU, no power last week
        "bottleneck_issues": ["GPU Shortage"],
        "themes": ["Compute"],
        "priority_areas": ["compute_capacity"],
        "sentiment": "neutral",
        "bottleneck_count": 1,
        "theme_count": 1,
        "takeaway_snippet": "GPU supply tight",
    }
    
    sig2 = evaluate_significance(week2, week1)
    print("\nResult:")
    print(json.dumps(sig2, indent=2))
