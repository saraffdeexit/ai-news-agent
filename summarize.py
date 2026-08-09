"""
summarize.py

Sends the week's fetched headlines to Claude and asks for a themed
digest with a dedicated "Bottlenecks & Constraints" section.

Uses tool-calling (a forced function call) rather than asking Claude to
freehand JSON as text. This guarantees schema-valid, already-parsed
output and avoids the failure mode where an article title containing a
quote or special character corrupts hand-written JSON.

Requires ANTHROPIC_API_KEY in the environment.
"""

import json
import os

import anthropic

from fetch_news import Article

MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """You are producing a concise weekly digest of AI industry \
news for a busy reader. You will be given a list of headlines with sources, \
publish dates, and links, gathered from the last 7 days.

Call the build_digest tool with your analysis. Guidelines:
- Group headlines into 3-6 sensible themes (e.g. Model Releases, Infrastructure & Compute, \
Funding & Business, Regulation & Policy, Talent). Skip themes with no relevant news.
- ALWAYS fill in "one_line_takeaway" — never leave it blank. Pick the single most important \
development across all the headlines, even if it's also covered inside a theme below.
- ALWAYS populate "bottlenecks" as its own list whenever ANY headline touches chip/GPU supply, \
power or energy constraints, data center capacity, talent shortages, regulatory friction, or data \
availability limits — even if you already covered that same content inside a "themes" entry (e.g. an \
"Infrastructure & Compute" theme). The bottlenecks list is a required, separately-curated highlight \
reel, not just a mirror of the themes — do not leave it empty unless truly nothing in the headlines \
relates to any constraint. Only return an empty list if you're confident no headline qualifies.
- Only include an article under a theme/bottleneck if it's genuinely representative; don't list \
every headline under every theme. Cap each theme and bottleneck at 3 article links max — pick the \
most representative ones, not every match.
- Keep summaries tight and factual. No speculation beyond what the headlines support.
"""

DIGEST_TOOL = {
    "name": "build_digest",
    "description": "Submit the structured weekly AI news digest.",
    "input_schema": {
        "type": "object",
        "properties": {
            "themes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "theme": {"type": "string"},
                        "summary": {"type": "string"},
                        "articles": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "link": {"type": "string"},
                                    "source": {"type": "string"},
                                },
                                "required": ["title", "link"],
                            },
                        },
                    },
                    "required": ["theme", "summary", "articles"],
                },
            },
            "bottlenecks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "issue": {"type": "string"},
                        "summary": {"type": "string"},
                        "articles": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "link": {"type": "string"},
                                    "source": {"type": "string"},
                                },
                                "required": ["title", "link"],
                            },
                        },
                    },
                    "required": ["issue", "summary", "articles"],
                },
            },
            "one_line_takeaway": {"type": "string"},
        },
        "required": ["themes", "bottlenecks", "one_line_takeaway"],
    },
}


def summarize_articles(articles: list[Article]) -> dict:
    if not articles:
        return {
            "themes": [],
            "bottlenecks": [],
            "one_line_takeaway": "No AI-related news found this week.",
        }

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    payload = [
        {
            "title": a.title,
            "source": a.source,
            "published": a.published,
            "link": a.link,
        }
        for a in articles
    ]

    message = client.messages.create(
        model=MODEL,
        max_tokens=6000,
        system=SYSTEM_PROMPT,
        tools=[DIGEST_TOOL],
        tool_choice={"type": "tool", "name": "build_digest"},
        messages=[
            {
                "role": "user",
                "content": f"Here are this week's headlines:\n\n{json.dumps(payload, indent=2)}",
            }
        ],
    )

    print(f"[summarize] stop_reason={message.stop_reason}, "
          f"usage={message.usage}, content_blocks={len(message.content)}")

    if message.stop_reason == "max_tokens":
        print("[summarize] WARNING: response hit max_tokens — tool call was likely truncated.")

    for block in message.content:
        print(f"[summarize] block type={block.type}"
              + (f", tool_name={block.name}, input_keys={list(block.input.keys()) if hasattr(block, 'input') else None}"
                 if block.type == "tool_use" else ""))
        if block.type == "tool_use" and block.name == "build_digest":
            if not block.input:
                raise RuntimeError(
                    f"build_digest was called with empty input. stop_reason={message.stop_reason}"
                )
            result = block.input
            if not result.get("one_line_takeaway") and result.get("themes"):
                result["one_line_takeaway"] = result["themes"][0].get("summary", "")
            return result

    raise RuntimeError(f"Claude did not return a build_digest tool call. stop_reason={message.stop_reason}")


if __name__ == "__main__":
    from fetch_news import fetch_articles

    result = summarize_articles(fetch_articles())
    print(json.dumps(result, indent=2))
