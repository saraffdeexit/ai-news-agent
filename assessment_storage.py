"""
assessment_storage.py

Persists daily assessments to disk with timestamps. Allows loading
previous assessments for comparison (V2+).

Stores assessments as JSON files in ./assessments/ directory, one per day.
Filename: YYYY-MM-DD.json

Structure:
{
  "date": "2025-01-15",
  "timestamp": "2025-01-15T08:30:00Z",
  "article_count": 42,
  "themes": [...],
  "bottlenecks": [...],
  "one_line_takeaway": "...",
  "assessment_summary": "..." (human-readable summary for comparison)
}
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

STORAGE_DIR = Path("./assessments")


def ensure_storage_dir() -> Path:
    """Create the assessments directory if it doesn't exist."""
    STORAGE_DIR.mkdir(exist_ok=True)
    return STORAGE_DIR


def get_assessment_path(date_str: str = None) -> Path:
    """Get the storage path for a given date. Default is today."""
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return STORAGE_DIR / f"{date_str}.json"


def save_assessment(digest: dict, article_count: int = 0) -> dict:
    """
    Save today's assessment. Adds metadata (date, timestamp, article_count).
    Returns the complete assessment object.
    """
    ensure_storage_dir()

    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")

    # Build a human-readable summary for easier comparison
    summary_parts = []
    if digest.get("one_line_takeaway"):
        summary_parts.append(f"Takeaway: {digest['one_line_takeaway']}")

    if digest.get("bottlenecks"):
        issues = [b.get("issue", "") for b in digest["bottlenecks"]]
        summary_parts.append(f"Bottlenecks: {', '.join(issues)}")

    if digest.get("themes"):
        themes = [t.get("theme", "") for t in digest["themes"]]
        summary_parts.append(f"Themes: {', '.join(themes)}")

    assessment = {
        "date": date_str,
        "timestamp": now.isoformat(),
        "article_count": article_count,
        "themes": digest.get("themes", []),
        "bottlenecks": digest.get("bottlenecks", []),
        "one_line_takeaway": digest.get("one_line_takeaway", ""),
        "assessment_summary": "\n".join(summary_parts),
    }

    path = get_assessment_path(date_str)
    with open(path, "w") as f:
        json.dump(assessment, f, indent=2)

    print(f"[assessment_storage] Saved assessment to {path}")
    return assessment


def load_assessment(date_str: str = None) -> dict | None:
    """
    Load an assessment from disk. Returns None if not found.
    Default is today; pass YYYY-MM-DD to load a specific date.
    """
    path = get_assessment_path(date_str)
    if not path.exists():
        return None

    with open(path, "r") as f:
        return json.load(f)


def load_previous_assessment() -> dict | None:
    """
    Load the most recent assessment from before today.
    Used for V2+ comparison.
    """
    ensure_storage_dir()

    files = sorted(STORAGE_DIR.glob("*.json"), reverse=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for file in files:
        date_str = file.stem  # e.g., "2025-01-15"
        if date_str < today:  # Find the first file before today
            with open(file, "r") as f:
                return json.load(f)

    return None


def list_assessments() -> list[dict]:
    """
    List all saved assessments in reverse chronological order.
    Useful for debugging or manual inspection.
    """
    ensure_storage_dir()

    assessments = []
    for file in sorted(STORAGE_DIR.glob("*.json"), reverse=True):
        with open(file, "r") as f:
            assessments.append(json.load(f))

    return assessments


if __name__ == "__main__":
    # Test the storage layer
    test_digest = {
        "themes": [{"theme": "Model Releases", "summary": "New models from OpenAI and Anthropic."}],
        "bottlenecks": [{"issue": "GPU Supply", "summary": "H100 shortage continues."}],
        "one_line_takeaway": "GPU shortage drives alternative chip development.",
    }

    saved = save_assessment(test_digest, article_count=42)
    print(f"\nSaved assessment:\n{json.dumps(saved, indent=2)}")

    loaded = load_assessment()
    print(f"\nLoaded assessment:\n{json.dumps(loaded, indent=2)}")

    prev = load_previous_assessment()
    if prev:
        print(f"\nPrevious assessment (before today):\n{json.dumps(prev, indent=2)}")
    else:
        print("\nNo previous assessment found.")
