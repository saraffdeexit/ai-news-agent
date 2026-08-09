"""
send_email.py

Renders the digest JSON into an HTML email and sends it via Gmail SMTP
using an app password (same pattern as Fred-Agent).

Requires in the environment:
  GMAIL_ADDRESS       - the sending Gmail account
  GMAIL_APP_PASSWORD  - a Gmail app password (not your normal password)
  DIGEST_RECIPIENT    - where to send the digest (can equal GMAIL_ADDRESS)
"""

import datetime as dt
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def _render_article_links(articles: list[dict]) -> str:
    items = "".join(
        f'<li><a href="{a["link"]}">{a["title"]}</a>'
        f'<span style="color:#888;"> — {a.get("source", "")}</span></li>'
        for a in articles
    )
    return f'<ul style="margin:4px 0 12px 0; padding-left:20px;">{items}</ul>'


def render_html(digest: dict) -> str:
    today = dt.date.today().strftime("%B %d, %Y")

    bottleneck_html = ""
    if digest.get("bottlenecks"):
        rows = ""
        for b in digest["bottlenecks"]:
            rows += f"""
            <div style="background:#FFF4E5; border-left:4px solid #E8871E; padding:10px 14px; margin-bottom:12px; border-radius:4px;">
              <div style="font-weight:bold; color:#8A4B00;">{b['issue']}</div>
              <div style="margin:4px 0;">{b['summary']}</div>
              {_render_article_links(b.get('articles', []))}
            </div>
            """
        bottleneck_html = f"""
        <h2 style="color:#8A4B00;">⚠️ Bottlenecks &amp; Constraints</h2>
        {rows}
        """

    theme_html = ""
    for t in digest.get("themes", []):
        theme_html += f"""
        <div style="margin-bottom:18px;">
          <h3 style="margin-bottom:4px;">{t['theme']}</h3>
          <div style="margin:4px 0;">{t['summary']}</div>
          {_render_article_links(t.get('articles', []))}
        </div>
        """

    takeaway = digest.get("one_line_takeaway", "")

    return f"""
    <html>
    <body style="font-family: -apple-system, Arial, sans-serif; color:#222; max-width:680px; margin:auto;">
      <h1 style="margin-bottom:0;">AI Development Weekly Digest</h1>
      <div style="color:#888; margin-bottom:20px;">{today}</div>

      <div style="background:#F0F4FF; border-left:4px solid #3B5BDB; padding:10px 14px; margin-bottom:20px; border-radius:4px;">
        <strong>This week in one line:</strong> {takeaway}
      </div>

      {bottleneck_html}

      <h2>By Theme</h2>
      {theme_html}

      <div style="color:#aaa; font-size:12px; margin-top:30px;">
        Generated automatically from Google News RSS + Claude. Sources linked above.
      </div>
    </body>
    </html>
    """


def send_digest(digest: dict) -> None:
    gmail_address = os.environ["GMAIL_ADDRESS"].strip()
    gmail_app_password = os.environ["GMAIL_APP_PASSWORD"]
    # Strip all whitespace, including non-breaking spaces (\xa0) that sneak in
    # when copy-pasting the app password from Google's "abcd efgh ijkl mnop"
    # display format.
    gmail_app_password = "".join(gmail_app_password.split())

    # DIGEST_RECIPIENT can be a single address or a comma-separated list,
    # e.g. "you@gmail.com, spouse@gmail.com"
    raw_recipients = os.environ.get("DIGEST_RECIPIENT", gmail_address)
    recipients = [r.strip() for r in raw_recipients.split(",") if r.strip()]

    html = render_html(digest)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"AI Weekly Digest — {dt.date.today().strftime('%b %d, %Y')}"
    msg["From"] = gmail_address
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_address, gmail_app_password)
        server.sendmail(gmail_address, recipients, msg.as_string())

    print(f"Digest sent to {', '.join(recipients)}")


if __name__ == "__main__":
    # quick manual test with a fake digest
    fake_digest = {
        "one_line_takeaway": "Test run — no real data.",
        "bottlenecks": [
            {
                "issue": "Example bottleneck",
                "summary": "This is a test row.",
                "articles": [{"title": "Example article", "link": "https://example.com", "source": "Example"}],
            }
        ],
        "themes": [
            {
                "theme": "Example Theme",
                "summary": "This is a test summary.",
                "articles": [{"title": "Example article", "link": "https://example.com", "source": "Example"}],
            }
        ],
    }
    send_digest(fake_digest)
