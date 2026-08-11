"""
send_email_v34.py

V3/V4 Enhanced email sending:
- V3: Only sends if significant changes detected (watchdog mode)
- V4: Includes investigation findings and confidence score

Falls back to sending full digest on Friday regardless (to keep user in loop).

Pass either:
1. Full digest mode: digest dict (sends full digest)
2. Alert mode: digest, comparison, investigation dicts (sends alert with findings)
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


def render_alert_html(digest: dict, comparison: dict, investigation: dict = None) -> str:
    """
    Render an alert-style email (V3+) when changes are significant.
    Shows what changed and investigation findings (if available).
    """
    today = dt.date.today().strftime("%B %d, %Y")
    changes = comparison.get("changes", {})
    score = comparison.get("significance_score", 0)
    reason = comparison.get("significance_reason", "")

    # Change highlights
    change_html = ""
    if changes.get("new_bottlenecks"):
        issues = [b.get("issue", "") for b in changes["new_bottlenecks"]]
        change_html += f"""
        <div style="margin-bottom:12px; padding:8px; background:#FFF4E5; border-left:4px solid #E8871E; border-radius:4px;">
          <strong style="color:#8A4B00;">🚨 New Bottlenecks</strong>
          <div style="margin-top:4px;">{', '.join(issues)}</div>
        </div>
        """

    if changes.get("shifted_themes"):
        themes = changes["shifted_themes"]
        change_html += f"""
        <div style="margin-bottom:12px; padding:8px; background:#EBF5FB; border-left:4px solid #3B5BDB; border-radius:4px;">
          <strong style="color:#1E3A8A;">📊 New Themes Emerging</strong>
          <div style="margin-top:4px;">{', '.join(themes)}</div>
        </div>
        """

    if changes.get("takeaway_changed"):
        change_html += f"""
        <div style="margin-bottom:12px; padding:8px; background:#F0FDF4; border-left:4px solid #22C55E; border-radius:4px;">
          <strong style="color:#166534;">↗️ Takeaway Shifted</strong>
          <div style="margin-top:4px;">{digest.get('one_line_takeaway', '')}</div>
        </div>
        """

    # Investigation section
    investigation_html = ""
    if investigation and investigation.get("investigated"):
        inv_summary = investigation.get("investigation_summary", "")
        confidence = 60 + investigation.get("confidence_uplift", 0)
        investigation_html = f"""
        <div style="margin-bottom:20px; padding:12px; background:#F9F5FF; border-left:4px solid #9333EA; border-radius:4px;">
          <strong style="color:#581C87;">🔍 Investigation Findings</strong>
          <div style="margin-top:8px; font-size:13px; line-height:1.5;">{inv_summary}</div>
          <div style="margin-top:8px; font-size:11px; color:#666;">Confidence: {confidence}%</div>
        </div>
        """

    return f"""
    <html>
    <body style="font-family: -apple-system, Arial, sans-serif; color:#222; max-width:680px; margin:auto;">
      <h1 style="margin-bottom:0;">🔔 AI News Alert</h1>
      <div style="color:#888; margin-bottom:20px;">Significant changes detected • {today}</div>

      <div style="background:#FEF3C7; border-left:4px solid #D97706; padding:10px 14px; margin-bottom:20px; border-radius:4px;">
        <strong style="color:#92400E;">⚠️ Significance Score: {score}/100</strong>
        <div style="margin-top:4px; font-size:13px;">{reason}</div>
      </div>

      <h2 style="color:#E8871E; margin-top:20px;">What Changed</h2>
      {change_html}

      {investigation_html}

      <h2 style="margin-top:20px;">Full Digest Context</h2>
      <div style="background:#F9FAFB; padding:12px; border-radius:4px; font-size:13px;">
        <strong>{digest.get('one_line_takeaway', '')}</strong>
        <p style="margin:8px 0; color:#666;">
          Analyzed {digest.get('article_count', 0)} articles across {len(digest.get('themes', []))} themes.
        </p>
      </div>

      <div style="color:#aaa; font-size:12px; margin-top:30px;">
        🤖 AI Watchdog Agent • Auto-generated from Google News + Claude
      </div>
    </body>
    </html>
    """


def render_digest_html(digest: dict, article_count: int = 0) -> str:
    """Original digest HTML (for full Friday digest or manual send)."""
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


def send_email(
    digest: dict,
    recipient: str = None,
    alert_mode: bool = False,
    comparison: dict = None,
    investigation: dict = None,
) -> bool:
    """
    Send email. V3/V4 modes:
    - alert_mode=False: send full digest (original V1 behavior)
    - alert_mode=True: send alert with changes and investigation (V3/V4 behavior)

    Returns True if sent, False otherwise.
    """
    gmail_address = os.environ["GMAIL_ADDRESS"].strip()
    gmail_app_password = os.environ["GMAIL_APP_PASSWORD"]
    gmail_app_password = "".join(gmail_app_password.split())

    raw_recipients = recipient or os.environ.get("DIGEST_RECIPIENT", gmail_address)
    recipients = [r.strip() for r in raw_recipients.split(",") if r.strip()]

    if alert_mode and comparison:
        html = render_alert_html(digest, comparison, investigation)
        subject = f"🔔 AI Alert — Significant Changes ({comparison.get('significance_score', 0)}/100)"
    else:
        html = render_digest_html(digest)
        subject = f"AI Weekly Digest — {dt.date.today().strftime('%b %d, %Y')}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_address
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_address, gmail_app_password)
            server.sendmail(gmail_address, recipients, msg.as_string())
        print(f"[send_email] Sent to {', '.join(recipients)}")
        return True
    except Exception as e:
        print(f"[send_email] Failed to send: {e}")
        return False


if __name__ == "__main__":
    # Test alert mode
    test_digest = {
        "themes": [{"theme": "Model Releases", "summary": "New models."}],
        "bottlenecks": [{"issue": "GPU Supply", "summary": "Shortage."}],
        "one_line_takeaway": "GPU shortage worsens.",
        "article_count": 42,
    }

    test_comparison = {
        "significance_score": 75,
        "significance_reason": "New GPU supply bottleneck emerged.",
        "changes": {
            "new_bottlenecks": [{"issue": "Power consumption", "summary": "..."}],
            "shifted_themes": ["Energy Constraints"],
            "takeaway_changed": True,
        },
    }

    test_investigation = {
        "investigated": True,
        "investigation_summary": "Search results confirm power constraints are becoming critical.",
        "confidence_uplift": 15,
    }

    html_alert = render_alert_html(test_digest, test_comparison, test_investigation)
    print("Alert HTML preview:\n")
    print(html_alert[:500] + "...\n")

    html_digest = render_digest_html(test_digest)
    print("Digest HTML preview:\n")
    print(html_digest[:500] + "...")
