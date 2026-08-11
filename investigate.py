"""
investigate.py

V4 Autonomous Investigation: When significance.is_significant == True,
the watchdog automatically searches for more context/evidence before alerting.

This layer turns the digest + significance flag into a richer alert:
  1. Identify what changed (from significance.key_changes)
  2. Search for corroborating/explanatory news (company announcements, filings, etc.)
  3. Assess confidence level
  4. Attach investigation findings to the alert

Searches are targeted to avoid noise — e.g. if GPU shortage escalated,
search for NVIDIA capacity news, upcoming fab investments, etc.
"""

import json
import os
import anthropic


INVESTIGATION_PROMPT = """You are investigating a significant shift in AI industry news.

You will be given:
- The detected change (e.g. "New GPU shortage bottleneck", "Regulation escalating")
- Recent news snippets that might be related

Your job:
1. Analyze the evidence: does the news support/explain the detected change?
2. Identify corroborating signals (e.g. if regulation escalated, look for policy news, regulatory filings, etc.)
3. Rate confidence in the change (how confident are you this is a real trend vs. noise)
4. Suggest what deeper investigation might be needed

Return JSON with:
- finding: 1-2 sentence summary of investigation results
- supporting_evidence: list of key supporting news items (max 3)
- confidence: 0.0-1.0
- recommended_actions: what the human should look into next
"""

INVESTIGATION_TOOL = {
    "name": "submit_investigation",
    "description": "Submit autonomous investigation findings.",
    "input_schema": {
        "type": "object",
        "properties": {
            "finding": {"type": "string"},
            "supporting_evidence": {
                "type": "array",
                "items": {"type": "string"},
                "maxItems": 3,
            },
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "recommended_actions": {
                "type": "array",
                "items": {"type": "string"},
                "maxItems": 3,
            },
        },
        "required": ["finding", "supporting_evidence", "confidence", "recommended_actions"],
    },
}


def _build_search_queries(significance: dict, digest: dict) -> list[str]:
    """
    Generate targeted search queries based on what changed.
    
    Args:
        significance: from compare.evaluate_significance()
        digest: the full digest
    
    Returns:
        list of search queries to investigate
    """
    queries = []
    change_type = significance.get("change_type", "none")
    key_changes = significance.get("key_changes", [])
    
    # Rule-based query generation based on change_type
    if change_type == "new_issue":
        # Search for news about the new issue
        for change in key_changes:
            queries.append(f'"{change}" 2024 2025 news')
            queries.append(f'{change} announcement OR update')
    
    elif change_type == "escalation":
        # Search for escalating severity signals
        if any("gpu" in c.lower() for c in key_changes):
            queries.extend([
                "NVIDIA capacity 2025",
                "GPU shortage latest",
                "semiconductor fab investment",
            ])
        
        if any("power" in c.lower() for c in key_changes):
            queries.extend([
                "data center power crisis 2025",
                "electricity cost AI infrastructure",
                "renewable energy data centers",
            ])
        
        if any("regulation" in c.lower() for c in key_changes):
            queries.extend([
                "AI regulation 2025",
                "EU AI Act enforcement",
                "Biden AI executive order impact",
            ])
    
    elif change_type == "new_theme":
        # Search for emerging topic
        for change in key_changes:
            queries.append(f'{change} AI 2025')
    
    # Always add a general "what changed this week" query
    takeaway = digest.get("one_line_takeaway", "")[:50]
    if takeaway:
        queries.append(f'{takeaway}')
    
    # Limit to avoid too many searches
    return queries[:5]


def investigate(significance: dict, digest: dict, articles: list) -> dict:
    """
    Perform autonomous investigation when significance detected.
    
    Args:
        significance: output from compare.evaluate_significance()
        digest: the full digest
        articles: list of fetched articles for context
    
    Returns:
        investigation dict with findings, evidence, confidence
    """
    
    if not significance.get("is_significant"):
        return {
            "triggered": False,
            "reason": "Significance below threshold",
        }
    
    print("\n[investigate] Significant change detected, launching investigation...")
    
    change_type = significance.get("change_type", "unknown")
    key_changes = significance.get("key_changes", [])
    
    # Generate targeted search queries
    search_queries = _build_search_queries(significance, digest)
    print(f"[investigate] Generated {len(search_queries)} search queries: {search_queries}")
    
    # Simulate evidence gathering from existing articles
    # (In production, you'd do actual web searches here via API)
    related_articles = []
    articles_text = "\n".join([f"- {a.get('title', '')}" for a in articles[:5]])
    
    # Build context for Claude to analyze
    investigation_context = f"""
DETECTED CHANGE: {change_type}
KEY CHANGES: {json.dumps(key_changes)}

SIGNIFICANCE ANALYSIS:
{json.dumps(significance, indent=2)}

RECENT NEWS (related to change):
{articles_text}

Investigate: Is this change real? What's the evidence? What should be monitored?
"""
    
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=800,
        system=INVESTIGATION_PROMPT,
        tools=[INVESTIGATION_TOOL],
        tool_choice={"type": "tool", "name": "submit_investigation"},
        messages=[
            {
                "role": "user",
                "content": investigation_context,
            }
        ],
    )
    
    print(f"[investigate] Investigation complete: {message.stop_reason}")
    
    for block in message.content:
        if block.type == "tool_use" and block.name == "submit_investigation":
            result = block.input
            result["triggered"] = True
            result["change_detected"] = change_type
            print(f"[investigate] Confidence: {result.get('confidence')}, "
                  f"Actions: {len(result.get('recommended_actions', []))}")
            return result
    
    raise RuntimeError("Claude did not return investigation results")


if __name__ == "__main__":
    # Test mock data
    sig = {
        "is_significant": True,
        "change_type": "escalation",
        "key_changes": ["GPU shortage escalated to critical"],
        "reasoning": "Sentiment shifted from neutral to bearish, GPU shortage now prominent",
        "confidence": 0.85,
    }
    
    digest = {
        "one_line_takeaway": "NVIDIA reports record demand, supply crisis worsens.",
        "bottlenecks": [
            {
                "issue": "GPU Shortage",
                "summary": "Severe capacity constraints",
                "articles": [
                    {"title": "NVIDIA H100 supply crisis", "link": "...", "source": "TechCrunch"}
                ],
            }
        ],
        "themes": [],
    }
    
    articles = [
        {"title": "NVIDIA capacity", "source": "Reuters"},
        {"title": "GPU bottleneck", "source": "VentureBeat"},
    ]
    
    inv = investigate(sig, digest, articles)
    print("\n" + json.dumps(inv, indent=2))
