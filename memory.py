"""
memory.py

Manages persistent storage of weekly assessments and digest history.
Uses a single JSON file (assessments.json) to store timestamped entries.

Each entry contains:
  - date: ISO date of the assessment
  - digest: the full digest (themes, bottlenecks, takeaway)
  - assessment: normalized "state" for comparison (bottleneck list, themes, priority areas)
  - significance: (for V3+) whether this week's changes were significant
  - investigation: (for V4) results of autonomous investigation if significant
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ASSESSMENT_FILE = "assessments.json"


def _ensure_file():
    """Create empty assessment file if it doesn't exist."""
    if not Path(ASSESSMENT_FILE).exists():
        Path(ASSESSMENT_FILE).write_text(json.dumps({"assessments": []}, indent=2))


def load_history() -> list[dict]:
    """Load all stored assessments."""
    _ensure_file()
    with open(ASSESSMENT_FILE, "r") as f:
        data = json.load(f)
    return data.get("assessments", [])


def get_latest_assessment() -> Optional[dict]:
    """Get the most recent assessment."""
    history = load_history()
    return history[-1] if history else None


def get_previous_assessment(days_back: int = 7) -> Optional[dict]:
    """Get an assessment from ~N days ago."""
    history = load_history()
    if len(history) < 2:
        return None
    return history[-2]  # simplified: just get the previous one


def save_assessment(digest: dict, assessment: dict, significance: Optional[dict] = None, investigation: Optional[dict] = None) -> None:
    """
    Save a new assessment entry.
    
    Args:
        digest: the full digest (themes, bottlenecks, takeaway)
        assessment: normalized state (bottleneck_topics, themes, priority_areas)
        significance: (optional) significance analysis from V3
        investigation: (optional) investigation results from V4
    """
    _ensure_file()
    
    entry = {
        "date": datetime.now(timezone.utc).isoformat(),
        "digest": digest,
        "assessment": assessment,
    }
    if significance:
        entry["significance"] = significance
    if investigation:
        entry["investigation"] = investigation
    
    history = load_history()
    history.append(entry)
    
    with open(ASSESSMENT_FILE, "w") as f:
        json.dump({"assessments": history}, f, indent=2)
    
    print(f"[memory] Saved assessment to {ASSESSMENT_FILE}")


def print_history_summary():
    """Debug: print a summary of stored assessments."""
    history = load_history()
    print(f"\n[memory] Assessment history ({len(history)} entries):")
    for entry in history:
        date = entry.get("date", "unknown")[:10]
        takeaway = entry.get("digest", {}).get("one_line_takeaway", "")[:60]
        sig = "✓" if entry.get("significance", {}).get("is_significant") else "—"
        print(f"  {date} [{sig}] {takeaway}")


if __name__ == "__main__":
    print_history_summary()
