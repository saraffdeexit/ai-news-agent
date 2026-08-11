"""
assessment.py

Extracts a normalized "state" from the digest for comparison purposes.
This is the V2 → V3 layer: what we're comparing week-to-week to detect change.

Assessment structure:
  - bottleneck_topics: list of CANONICAL bottleneck categories (semantic equivalence)
  - bottleneck_issues: list of RAW issue names (for context in alerts)
  - themes: list of theme names (e.g. "Model Releases", "Regulation", "Compute")
  - priority_areas: high-level areas of concern/focus
  - sentiment: overall sentiment about the week (bullish/neutral/bearish)

Key: bottleneck_topics are CANONICAL (e.g., "compute_capacity") to avoid false positives
from wording changes. "GPU shortage" and "NVIDIA capacity crisis" both map to the same
canonical form, so they're recognized as the same underlying issue.
"""

from typing import Any

# Map bottleneck descriptions to canonical categories
# This prevents false positives when the same issue is described differently week-to-week
BOTTLENECK_SYNONYMS = {
    # Compute / GPU / chip
    "gpu shortage": "compute_capacity",
    "gpu shortages": "compute_capacity",
    "gpu supply shortage": "compute_capacity",
    "gpu capacity": "compute_capacity",
    "nvidia capacity": "compute_capacity",
    "nvidia capacity crisis": "compute_capacity",
    "nvidia capacity constraint": "compute_capacity",
    "h100 shortage": "compute_capacity",
    "h100 supply": "compute_capacity",
    "chip shortage": "compute_capacity",
    "chip supply": "compute_capacity",
    "chip supply crisis": "compute_capacity",
    "semiconductor shortage": "compute_capacity",
    "semiconductor supply": "compute_capacity",
    "compute bottleneck": "compute_capacity",
    "compute capacity": "compute_capacity",
    "compute constraint": "compute_capacity",
    "training capacity": "compute_capacity",
    "inference capacity": "compute_capacity",
    "hardware bottleneck": "compute_capacity",
    
    # Power / energy
    "power constraints": "power_energy",
    "power constraint": "power_energy",
    "power shortage": "power_energy",
    "power crisis": "power_energy",
    "electricity cost": "power_energy",
    "energy cost": "power_energy",
    "data center power": "power_energy",
    "data center power crisis": "power_energy",
    "power consumption": "power_energy",
    "energy constraint": "power_energy",
    
    # Regulation / policy
    "regulation": "regulation_policy",
    "ai regulation": "regulation_policy",
    "ai policy": "regulation_policy",
    "eu ai act": "regulation_policy",
    "regulatory friction": "regulation_policy",
    "compliance": "regulation_policy",
    "compliance friction": "regulation_policy",
    "government policy": "regulation_policy",
    "legal risk": "regulation_policy",
    
    # Talent / hiring
    "talent shortage": "talent_acquisition",
    "talent shortage": "talent_acquisition",
    "talent acquisition": "talent_acquisition",
    "researcher hiring": "talent_acquisition",
    "hiring competition": "talent_acquisition",
    "talent retention": "talent_acquisition",
    "brain drain": "talent_acquisition",
    "researcher exodus": "talent_acquisition",
    
    # Funding / valuations
    "funding round": "funding_valuations",
    "funding shortage": "funding_valuations",
    "valuation pressure": "funding_valuations",
    "capital constraints": "funding_valuations",
    
    # Data / training data
    "training data shortage": "training_data",
    "data availability": "training_data",
    "data constraint": "training_data",
}


def _canonicalize_bottleneck(issue: str) -> str:
    """
    Map a bottleneck issue to its canonical category.
    Falls back to normalized version if not in synonyms.
    
    Args:
        issue: raw bottleneck issue text (e.g., "GPU Shortage")
    
    Returns:
        canonical form (e.g., "compute_capacity")
    """
    issue_lower = issue.lower().strip()
    
    # Direct lookup in synonyms
    if issue_lower in BOTTLENECK_SYNONYMS:
        return BOTTLENECK_SYNONYMS[issue_lower]
    
    # Fuzzy match: if issue contains any key, use that
    for key, canonical in BOTTLENECK_SYNONYMS.items():
        if key in issue_lower or issue_lower in key:
            return canonical
    
    # Fallback: normalize to snake_case
    normalized = issue_lower.replace(" & ", "_and_").replace(" ", "_")
    return normalized


def build_assessment(digest: dict) -> dict:
    """
    Convert a digest into a normalized assessment for comparison.
    
    Args:
        digest: output from summarize.py (themes, bottlenecks, one_line_takeaway)
    
    Returns:
        assessment: normalized state with bottleneck_topics (canonical), themes, priority_areas
    """
    
    # Extract bottleneck topics from the digest
    bottleneck_topics = []
    bottleneck_issues = []
    
    for bottleneck in digest.get("bottlenecks", []):
        issue = bottleneck.get("issue", "").strip()
        if issue:
            bottleneck_issues.append(issue)
            # Canonicalize: map "GPU Shortage" and "NVIDIA Capacity Crisis" both to "compute_capacity"
            canonical = _canonicalize_bottleneck(issue)
            bottleneck_topics.append(canonical)
    
    # Extract themes
    themes = []
    for theme in digest.get("themes", []):
        theme_name = theme.get("theme", "").strip()
        if theme_name:
            themes.append(theme_name)
    
    # Infer priority areas from canonical bottleneck topics + themes
    priority_areas = []
    
    bottleneck_str = " ".join(bottleneck_topics).lower()
    theme_str = " ".join(themes).lower()
    combined = bottleneck_str + " " + theme_str
    
    # Rule-based classification of priority areas based on canonical forms
    if "compute_capacity" in bottleneck_topics:
        priority_areas.append("compute_capacity")
    
    if "power_energy" in bottleneck_topics:
        priority_areas.append("power_energy")
    
    if "regulation_policy" in bottleneck_topics:
        priority_areas.append("regulation_policy")
    
    if "talent_acquisition" in bottleneck_topics:
        priority_areas.append("talent_acquisition")
    
    if "funding_valuations" in bottleneck_topics:
        priority_areas.append("funding_valuations")
    
    if "training_data" in bottleneck_topics:
        priority_areas.append("training_data")
    
    if any(w in combined for w in ["model", "llm", "foundation", "release", "capability", "gpt", "claude", "gemini"]):
        priority_areas.append("model_capabilities")
    
    # Infer sentiment from takeaway + bottleneck count
    takeaway = digest.get("one_line_takeaway", "").lower()
    sentiment = "neutral"
    
    # Use unique canonical topics for sentiment inference
    unique_topics = len(set(bottleneck_topics))
    
    if unique_topics > 3:
        sentiment = "bearish"
    elif unique_topics > 1:
        sentiment = "neutral"
    else:
        sentiment = "bullish"
    
    # Negative keywords override to bearish
    if any(w in takeaway for w in ["shortage", "crisis", "constrain", "critical", "severe", "halt", "ban"]):
        sentiment = "bearish"
    
    return {
        "bottleneck_topics": sorted(set(bottleneck_topics)),  # canonical (for comparison)
        "bottleneck_issues": bottleneck_issues,  # raw (for context in alerts)
        "themes": themes,
        "priority_areas": sorted(set(priority_areas)),
        "sentiment": sentiment,
        "bottleneck_count": unique_topics,
        "theme_count": len(themes),
        "takeaway_snippet": takeaway[:100],
    }


if __name__ == "__main__":
    # Test 1: Basic assessment
    print("=== Test 1: Basic Assessment ===")
    fake_digest = {
        "one_line_takeaway": "GPU shortage worsens amid AI boom.",
        "bottlenecks": [
            {"issue": "GPU Shortage", "summary": "NVIDIA can't keep up", "articles": []},
            {"issue": "Power Constraints", "summary": "Data centers hitting limits", "articles": []},
        ],
        "themes": [
            {"theme": "Compute Bottlenecks", "summary": "...", "articles": []},
            {"theme": "Infrastructure", "summary": "...", "articles": []},
        ],
    }
    assessment = build_assessment(fake_digest)
    import json
    print(json.dumps(assessment, indent=2))
    
    # Test 2: Canonical equivalence (different wording, same issue)
    print("\n=== Test 2: Synonym Mapping (Same Issue, Different Wording) ===")
    fake_digest_2 = {
        "one_line_takeaway": "NVIDIA capacity crisis deepens.",
        "bottlenecks": [
            {"issue": "NVIDIA Capacity Crisis", "summary": "H100 waiting lists growing", "articles": []},
            {"issue": "Data Center Power Crisis", "summary": "Fabs hitting power limits", "articles": []},
        ],
        "themes": [
            {"theme": "Infrastructure", "summary": "...", "articles": []},
        ],
    }
    assessment_2 = build_assessment(fake_digest_2)
    print(json.dumps(assessment_2, indent=2))
    
    # Test 3: Show that canonical topics match (no false positives)
    print("\n=== Test 3: Comparison (No False Positive) ===")
    print(f"Week 1 canonical topics: {assessment['bottleneck_topics']}")
    print(f"Week 2 canonical topics: {assessment_2['bottleneck_topics']}")
    if assessment['bottleneck_topics'] == assessment_2['bottleneck_topics']:
        print("✓ Same underlying issues (canonical forms match)")
        print("✓ Would NOT trigger escalation alert (correct!)")
    else:
        print("✗ Different issues detected (canonical forms differ)")
    
    # Test 4: Show raw issues (for context)
    print("\n=== Test 4: Raw Issues (For Alert Context) ===")
    print(f"Week 1 raw issues: {assessment['bottleneck_issues']}")
    print(f"Week 2 raw issues: {assessment_2['bottleneck_issues']}")
