"""
summarize.py

Sends the week's fetched headlines to Claude and asks for a themed
digest with a dedicated "Bottlenecks & Constraints" section.

Uses tool-calling (a forced function call) rather than asking Claude to
freehand JSON as text — guarantees schema-valid, already-parsed output.

Article references use short numeric IDs rather than full title/link/
source in the model's output. Google News links are long encoded URLs
(200+ chars), so asking Claude to reproduce them verbatim for every
article wastes output tokens and risks truncation. Instead Claude just
cites article IDs, and Python looks up the real title/link/source
afterward from the original fetched list.

Requires ANTHROPIC_API_KEY in the environment.
"""

import json
import os

import anthropic

from fetch_news import Article

MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """You are producing a concise weekly digest of AI industry \
news for a busy reader. You will be given a numbered list of headlines with \
sources and publish dates, gathered from the last 7 days. Each headline has \
a short numeric id — use that id to reference articles in your output, \
never reproduce the title or a link yourself.

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
- Each theme/bottleneck's "article_ids" should list up to 3 of the most representative article ids — \
just the numbers, e.g. [4, 17, 22]. Don't list every matching id.
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
                        "article_ids": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "maxItems": 3,
                        },
                    },
                    "required": ["theme", "summary", "article_ids"],
                },
            },
            "bottlenecks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "issue": {"type": "string"},
                        "summary": {"type": "string"},
                        "article_ids": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "maxItems": 3,
                        },
                    },
                    "required": ["issue", "summary", "article_ids"],
                },
            },
            "one_line_takeaway": {"type": "string"},
        },
        "required": ["themes", "bottlenecks", "one_line_takeaway"],
    },
}


def _resolve_ids(article_ids: list[int], id_lookup: dict[int, Article]) -> list[dict]:
    resolved = []
    for aid in article_ids or []:
        article = id_lookup.get(aid)
        if article:
            resolved.append({"title": article.title, "link": article.link, "source": article.source})
    return resolved


def summarize_articles(articles: list[Article]) -> dict:
    if not articles:
        return {
            "themes": [],
            "bottlenecks": [],
            "one_line_takeaway": "No AI-related news found this week.",
        }

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    id_lookup = {i: a for i, a in enumerate(articles)}
    payload = [
        {
            "id": i,
            "title": a.title,
            "source": a.source,
            "published": a.published,
        }
        for i, a in enumerate(articles)
    ]

    message = client.messages.create(
        model=MODEL,
        max_tokens=4000,
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
            raw = block.input

            result = {
                "themes": [
                    {
                        "theme": t.get("theme", ""),
                        "summary": t.get("summary", ""),
                        "articles": _resolve_ids(t.get("article_ids", []), id_lookup),
                    }
                    for t in raw.get("themes", [])
                ],
                "bottlenecks": [
                    {
                        "issue": b.get("issue", ""),
                        "summary": b.get("summary", ""),
                        "articles": _resolve_ids(b.get("article_ids", []), id_lookup),
                    }
                    for b in raw.get("bottlenecks", [])
                ],
                "one_line_takeaway": raw.get("one_line_takeaway", ""),
            }
            if not result["one_line_takeaway"] and result["themes"]:
                result["one_line_takeaway"] = result["themes"][0]["summary"]
            return result

    raise RuntimeError(f"Claude did not return a build_digest tool call. stop_reason={message.stop_reason}")


if __name__ == "__main__":
    from fetch_news import fetch_articles

    result = summarize_articles(fetch_articles())
    print(json.dumps(result, indent=2))
