"""
send_email_v4.py

Sends the watchdog alert email when significance detected (V3) + investigation results (V4).

Unlike send_email.py (which sends the full digest weekly), this only sends when
something materially changed, and includes:
  - Significance analysis (what changed, why it matters)
  - Investigation findings (corroborating evidence, recommended actions)
  - Condensed digest relevant to the change

Subject line reflects urgency: "[WATCHDOG] ..." for alerts.
"""

import datetime as dt
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def _render_significance_section(significance: dict) -> str:
    """Render the significance analysis section."""
    is_sig = significance.get("is_significant", False)
    change_type = significance.get("change_type", "unknown")
    reasoning = significance.get("reasoning", "")
    confidence = significance.get("confidence", 0)
    key_changes = significance.get("key_changes", [])
    
    change_type_display = {
        "new_issue": "🆕 New Issue Detected",
        "escalation": "⚠️ Escalation",
        "new_theme": "📍 New Theme Emerged",
        "resolved": "✓ Issue Resolved",
        "sentiment_shift": "📊 Sentiment Shift",
        "none": "No significant change",
    }.get(change_type, change_type)
    
    html = f"""
    <div style="background:#FFF4E5; border-left:6px solid #E8871E; padding:14px; margin-bottom:20px; border-radius:4px;">
      <div style="font-size:16px; font-weight:bold; color:#8A4B00; margin-bottom:8px;">
        {change_type_display}
      </div>
      <div style="color:#333; margin-bottom:10px;">{reasoning}</div>
      <div style="font-size:12px; color:#888;">Confidence: {confidence:.0%}</div>
    """
    
    if key_changes:
        html += f"""
      <div style="margin-top:10px; font-size:12px;">
        <strong>Key changes:</strong>
        <ul style="margin:4px 0; padding-left:18px;">
        """
        for change in key_changes:
            html += f'<li>{change}</li>'
        html += """
        </ul>
      </div>
        """
    
    html += "</div>"
    return html


def _render_investigation_section(investigation: dict) -> str:
    """Render the investigation findings section."""
    if not investigation or not investigation.get("triggered"):
        return ""
    
    finding = investigation.get("finding", "")
    confidence = investigation.get("confidence", 0)
    supporting = investigation.get("supporting_evidence", [])
    actions = investigation.get("recommended_actions", [])
    
    html = f"""
    <div style="background:#E8F5E9; border-left:6px solid #4CAF50; padding:14px; margin-bottom:20px; border-radius:4px;">
      <div style="font-size:16px; font-weight:bold; color:#2E7D32; margin-bottom:8px;">
        🔍 Investigation Findings
      </div>
      <div style="color:#333; margin-bottom:10px;">{finding}</div>
      <div style="font-size:12px; color:#888;">Confidence: {confidence:.0%}</div>
    """
    
    if supporting:
        html += f"""
      <div style="margin-top:10px;">
        <strong style="font-size:12px;">Supporting evidence:</strong>
        <ul style="margin:4px 0; padding-left:18px; font-size:12px;">
        """
        for evidence in supporting:
            html += f'<li>{evidence}</li>'
        html += """
        </ul>
      </div>
        """
    
    if actions:
        html += f"""
      <div style="margin-top:10px;">
        <strong style="font-size:12px;">Recommended next steps:</strong>
        <ul style="margin:4px 0; padding-left:18px; font-size:12px;">
        """
        for action in actions:
            html += f'<li>{action}</li>'
        html += """
        </ul>
      </div>
        """
    
    html += "</div>"
    return html


def _render_bottlenecks(digest: dict, assessment: dict = None) -> str:
    """
    Render the key bottlenecks from the digest.
    
    If assessment is provided, shows both raw issue names and their canonical forms
    to give context about what the watchdog is tracking.
    """
    bottlenecks = digest.get("bottlenecks", [])
    if not bottlenecks:
        return ""
    
    html = '<h2 style="color:#8A4B00;">Bottlenecks & Constraints</h2>'
    
    # Get canonical topics from assessment for reference
    canonical_topics = set(assessment.get("bottleneck_topics", [])) if assessment else set()
    canonical_map = {
        "compute_capacity": "Compute Capacity",
        "power_energy": "Power & Energy",
        "regulation_policy": "Regulation & Policy",
        "talent_acquisition": "Talent & Acquisition",
        "funding_valuations": "Funding & Valuations",
        "training_data": "Training Data",
        "model_capabilities": "Model Capabilities",
    }
    
    for b in bottlenecks:
        issue = b.get("issue", "")
        summary = b.get("summary", "")
        articles = b.get("articles", [])
        
        # Find which canonical category this issue belongs to
        canonical_label = ""
        if assessment and assessment.get("bottleneck_issues"):
            # Match this issue to see which canonical form it maps to
            issue_lower = issue.lower().strip()
            for canonical in canonical_topics:
                canonical_display = canonical_map.get(canonical, canonical)
                canonical_label = f' <span style="font-size:11px; color:#888;">({canonical_display})</span>'
                break
        
        html += f"""
        <div style="background:#FFF4E5; border-left:4px solid #E8871E; padding:10px 14px; margin-bottom:12px; border-radius:4px;">
          <div style="font-weight:bold; color:#8A4B00;">{issue}{canonical_label}</div>
          <div style="margin:4px 0; font-size:13px;">{summary}</div>
        """
        
        if articles:
            html += '<ul style="margin:6px 0; padding-left:18px; font-size:12px;">'
            for article in articles[:2]:  # limit to 2 articles per bottleneck
                html += f'<li><a href="{article.get("link", "#")}">{article.get("title", "")}</a></li>'
            html += '</ul>'
        
        html += '</div>'
    
    return html


def _render_themes(digest: dict) -> str:
    """Render the digest themes (V1 component) with summaries and articles."""
    themes = digest.get("themes", [])
    if not themes:
        return ""
    
    html = '<h2>By Theme</h2>'
    for t in themes:
        theme_name = t.get("theme", "")
        summary = t.get("summary", "")
        articles = t.get("articles", [])
        
        html += f"""
        <div style="margin-bottom:18px;">
          <h3 style="margin-bottom:4px;">{theme_name}</h3>
          <div style="margin:4px 0; font-size:13px;">{summary}</div>
        """
        
        if articles:
            html += '<ul style="margin:6px 0; padding-left:18px; font-size:12px;">'
            for article in articles:
                html += f'<li><a href="{article.get("link", "#")}">{article.get("title", "")}</a></li>'
            html += '</ul>'
        
        html += '</div>'
    
    return html


def render_alert_html(digest: dict, assessment: dict, significance: dict, 
                     investigation: dict = None) -> str:
    """Render the full watchdog alert email with V1-V4 layers."""
    
    today = dt.date.today().strftime("%B %d, %Y")
    takeaway = digest.get("one_line_takeaway", "")
    
    html = f"""
    <html>
    <body style="font-family: -apple-system, Arial, sans-serif; color:#222; max-width:680px; margin:auto;">
      <h1 style="margin-bottom:4px;">🚨 AI Watchdog Alert</h1>
      <div style="color:#888; margin-bottom:20px;">{today}</div>
      
      <div style="background:#F0F4FF; border-left:4px solid #3B5BDB; padding:10px 14px; margin-bottom:20px; border-radius:4px;">
        <strong>This week:</strong> {takeaway}
      </div>
      
      {_render_significance_section(significance)}
      
      {_render_investigation_section(investigation) if investigation else ''}
      
      {_render_bottlenecks(digest, assessment)}
      
      {_render_themes(digest)}
      
      <div style="margin-top:30px; padding-top:20px; border-top:1px solid #ddd; font-size:11px; color:#aaa;">
        <p>This alert was generated automatically when the AI watchdog detected a significant change in industry news. 
        The digest is based on Google News RSS + Claude analysis. Investigation findings use autonomous news analysis.</p>
        <p><strong>Assessment stored.</strong> Previous week's data is available for trend analysis.</p>
      </div>
    </body>
    </html>
    """
    
    return html


def send_alert(digest: dict, assessment: dict, significance: dict, investigation: dict = None) -> None:
    """
    Send a watchdog alert email.
    
    Args:
        digest: full digest from summarize.py
        assessment: normalized assessment from assessment.py
        significance: significance analysis from compare.py
        investigation: investigation results from investigate.py (optional)
    """
    
    gmail_address = os.environ["GMAIL_ADDRESS"].strip()
    gmail_app_password = os.environ["GMAIL_APP_PASSWORD"]
    gmail_app_password = "".join(gmail_app_password.split())
    
    raw_recipients = os.environ.get("DIGEST_RECIPIENT", gmail_address)
    recipients = [r.strip() for r in raw_recipients.split(",") if r.strip()]
    
    html = render_alert_html(digest, assessment, significance, investigation)
    
    # Alert subject indicates severity
    change_type = significance.get("change_type", "update")
    confidence = significance.get("confidence", 0)
    urgency = "🔴" if confidence > 0.8 else "🟡" if confidence > 0.6 else "🟢"
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[WATCHDOG] AI News Alert — {change_type.replace('_', ' ').title()} {urgency}"
    msg["From"] = gmail_address
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html, "html"))
    
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_address, gmail_app_password)
        server.sendmail(gmail_address, recipients, msg.as_string())
    
    print(f"✓ Alert sent to {', '.join(recipients)}")
    print(f"  Subject: [WATCHDOG] {change_type} {urgency}")
    print(f"  Confidence: {confidence:.0%}")


if __name__ == "__main__":
    # Test with mock data
    fake_digest = {
        "one_line_takeaway": "NVIDIA reports record demand, GPU shortage escalates.",
        "bottlenecks": [
            {
                "issue": "GPU Shortage",
                "summary": "NVIDIA H100s remain critically constrained.",
                "articles": [
                    {"title": "NVIDIA Capacity Crisis", "link": "https://example.com", "source": "TechCrunch"},
                    {"title": "H100 Waiting Lists", "link": "https://example.com", "source": "Reuters"},
                ],
            },
            {
                "issue": "Power Constraints",
                "summary": "Data centers hitting electrical grid capacity limits.",
                "articles": [
                    {"title": "Fab Expansion Delayed", "link": "https://example.com", "source": "VentureBeat"},
                    {"title": "Power Grid Alert", "link": "https://example.com", "source": "The Information"},
                ],
            }
        ],
        "themes": [
            {
                "theme": "Compute Bottlenecks",
                "summary": "Demand for H100s and A100s outpacing supply. Major cloud providers report waiting lists stretching to mid-2025.",
                "articles": [
                    {"title": "NVIDIA Q1 Earnings — Supply Limited", "link": "https://example.com"},
                    {"title": "GPU Waiting Times Rising", "link": "https://example.com"},
                    {"title": "Next-Gen Chip Delayed", "link": "https://example.com"},
                ],
            },
            {
                "theme": "Infrastructure & Scaling",
                "summary": "Data center power consumption becoming limiting factor. Multiple regions hitting electrical grid capacity.",
                "articles": [
                    {"title": "Power Grid Alert", "link": "https://example.com"},
                    {"title": "Fab Expansion Delayed", "link": "https://example.com"},
                    {"title": "Renewable Energy Shortage", "link": "https://example.com"},
                ],
            },
            {
                "theme": "Model Releases & Competition",
                "summary": "New open-source models launching weekly. Competition intensifying as frontier labs release capabilities.",
                "articles": [
                    {"title": "Llama 3.1 Released", "link": "https://example.com"},
                    {"title": "Open Source Momentum", "link": "https://example.com"},
                    {"title": "Smaller Models Perform Better", "link": "https://example.com"},
                ],
            },
        ],
    }
    
    fake_assessment = {
        "bottleneck_topics": ["gpu_shortage"],
        "themes": ["Compute"],
        "priority_areas": ["compute_capacity"],
        "sentiment": "bearish",
        "bottleneck_count": 1,
        "theme_count": 1,
        "takeaway_snippet": "GPU shortage",
    }
    
    fake_significance = {
        "is_significant": True,
        "reasoning": "GPU shortage escalated from neutral to bearish sentiment.",
        "change_type": "escalation",
        "key_changes": ["GPU shortage worsened"],
        "confidence": 0.85,
    }
    
    fake_investigation = {
        "triggered": True,
        "finding": "NVIDIA's latest earnings confirm supply constraints will persist through Q2 2025.",
        "supporting_evidence": [
            "NVIDIA Q1 earnings call — limited H100 supply through Q2",
            "Taiwan TSMC fab expansions delayed due to power constraints",
            "Multiple cloud providers reporting H100 waiting lists > 6 months",
        ],
        "confidence": 0.90,
        "recommended_actions": [
            "Monitor NVIDIA's next earnings call for supply guidance",
            "Track fab capacity announcements from TSMC, Samsung",
            "Watch for alternative GPU adoption (AMD MI300, Intel Gaudi)",
        ],
    }
    
    html = render_alert_html(fake_digest, fake_assessment, fake_significance, fake_investigation)
    
    # Print to see it
    with open("/tmp/watchdog_alert_test.html", "w") as f:
        f.write(html)
    
    print("Test HTML saved to /tmp/watchdog_alert_test.html")
