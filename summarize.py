"""
summarize.py

Sends the week's fetched headlines to Claude and asks for a themed
digest with a dedicated "Bottlenecks & Constraints" section.

Requires ANTHROPIC_API_KEY in the environment.
"""

import json
import os

import anthropic

from fetch_news import Article

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are producing a concise weekly digest of AI industry \
news for a busy reader. You will be given a list of headlines with sources, \
publish dates, and links, gathered from the last 7 days.

Return ONLY valid JSON (no markdown fences, no preamble) matching this shape:

{
  "themes": [
    {
      "theme": "Model Releases",
      "summary": "1-3 sentence synthesis of what happened this week in this theme.",
      "articles": [{"title": "...", "link": "...", "source": "..."}]
    }
  ],
  "bottlenecks": [
    {
      "issue": "Short label, e.g. 'HBM memory supply'",
      "summary": "1-2 sentences on the constraint and why it matters.",
      "articles": [{"title": "...", "link": "...", "source": "..."}]
    }
  ],
  "one_line_takeaway": "A single sentence capturing the week's most important development."
}

Guidelines:
- Group headlines into 3-6 sensible themes (e.g. Model Releases, Infrastructure & Compute, \
Funding & Business, Regulation & Policy, Talent). Skip themes with no relevant news.
- The "bottlenecks" section is the most important part: pull out anything related to chip/GPU \
supply, power or energy constraints, data center capacity, talent shortages, regulatory friction, \
or data availability limits. If nothing qualifies, return an empty list — don't force it.
- Only include an article under a theme/bottleneck if it's genuinely representative; don't list \
every headline under every theme.
- Keep summaries tight and factual. No speculation beyond what the headlines support.
"""


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
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Here are this week's headlines:\n\n{json.dumps(payload, indent=2)}",
            }
        ],
    )

    text = "".join(block.text for block in message.content if block.type == "text")
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    return json.loads(text)


if __name__ == "__main__":
    from fetch_news import fetch_articles

    result = summarize_articles(fetch_articles())
    print(json.dumps(result, indent=2))
