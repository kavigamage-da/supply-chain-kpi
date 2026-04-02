"""
email_report.py
---------------
Sends the KPI summary as an HTML email with the dashboard chart attached.

Supports two backends (set EMAIL_BACKEND in .env):
    smtp      — Gmail / any SMTP server (default)
    sendgrid  — SendGrid free tier (100 emails/day)

Usage:
    python scripts/email_report.py
"""

import os
import json
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
from email.mime.image     import MIMEImage
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────────────────────────────
EMAIL_BACKEND  = os.getenv("EMAIL_BACKEND", "smtp")
SMTP_HOST      = os.getenv("SMTP_HOST",     "smtp.gmail.com")
SMTP_PORT      = int(os.getenv("SMTP_PORT", "587"))
EMAIL_USER     = os.getenv("EMAIL_USER",    "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_TO       = os.getenv("EMAIL_TO",      "")
SENDGRID_KEY   = os.getenv("SENDGRID_API_KEY", "")

BASE_DIR       = Path(__file__).resolve().parent.parent
KPI_JSON       = BASE_DIR / "output" / "reports" / "kpi_summary.json"
DASHBOARD_PNG  = BASE_DIR / "output" / "charts"  / "kpi_dashboard.png"


# ── HTML template ────────────────────────────────────────────────────────────

def build_html(kpis: dict) -> str:
    overall   = kpis["overall"]
    warehouse = kpis["warehouse"]
    generated = kpis.get("generated_at", "—")

    wh_rows = "".join(
        f"<tr><td>{w['warehouse']}</td>"
        f"<td style='color:{'#3fb950' if w['on_time_rate_pct']>=80 else '#f85149'}'>"
        f"{w['on_time_rate_pct']}%</td>"
        f"<td>{w['avg_delay_days']:.2f}d</td>"
        f"<td>LKR {w['avg_cost_per_order']:,.0f}</td></tr>"
        for w in warehouse
    )

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>
  body      {{ font-family: 'Courier New', monospace; background:#0d1117; color:#e6edf3; margin:0; padding:20px; }}
  .card     {{ background:#161b22; border:1px solid #30363d; border-radius:8px; padding:20px; margin-bottom:16px; }}
  h1        {{ color:#58a6ff; font-size:1.4em; }}
  h2        {{ color:#8b949e; font-size:1em; margin:0 0 12px; }}
  .kpi-grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:12px; }}
  .kpi      {{ background:#0d1117; border-radius:6px; padding:12px; text-align:center; }}
  .kpi span {{ display:block; font-size:1.8em; font-weight:bold; }}
  .green    {{ color:#3fb950; }}
  .yellow   {{ color:#d29922; }}
  .red      {{ color:#f85149; }}
  table     {{ width:100%; border-collapse:collapse; font-size:.9em; }}
  th        {{ color:#8b949e; text-align:left; padding:6px 8px; border-bottom:1px solid #30363d; }}
  td        {{ padding:6px 8px; border-bottom:1px solid #21262d; }}
  .footer   {{ color:#8b949e; font-size:.75em; text-align:center; margin-top:20px; }}
</style>
</head>
<body>
<div class="card">
  <h1>🚚 Supply Chain KPI Report</h1>
  <p style="color:#8b949e;margin:0">Generated: {generated} &nbsp;|&nbsp; Automated by GitHub Actions</p>
</div>

<div class="card">
  <h2>OVERALL PERFORMANCE</h2>
  <div class="kpi-grid">
    <div class="kpi">
      <span class="{'green' if overall['on_time_rate_pct']>=80 else 'yellow'}">{overall['on_time_rate_pct']}%</span>
      On-Time Delivery
    </div>
    <div class="kpi">
      <span class="blue">{overall['total_orders']:,}</span>
      Total Orders
    </div>
    <div class="kpi">
      <span class="yellow">LKR {overall['avg_cost_per_order']:,.0f}</span>
      Avg Cost / Order
    </div>
    <div class="kpi">
      <span class="red">{overall['cancelled_orders']:,}</span>
      Cancelled
    </div>
    <div class="kpi">
      <span class="yellow">{overall['avg_delay_days']:.2f}d</span>
      Avg Delay
    </div>
    <div class="kpi">
      <span class="green">LKR {overall['total_revenue_lkr']/1_000_000:.1f}M</span>
      Total Revenue
    </div>
  </div>
</div>

<div class="card">
  <h2>WAREHOUSE BREAKDOWN</h2>
  <table>
    <tr><th>Warehouse</th><th>On-Time</th><th>Avg Delay</th><th>Avg Cost</th></tr>
    {wh_rows}
  </table>
</div>

<div class="card" style="text-align:center">
  <h2>DASHBOARD CHART</h2>
  <img src="cid:dashboard" style="width:100%;border-radius:6px" alt="KPI Dashboard"/>
</div>

<p class="footer">
  Supply Chain KPI Automation — Sysco LABS Portfolio Project<br/>
  Data pipeline runs daily via GitHub Actions. Source: orders_clean.csv
</p>
</body>
</html>
"""


# ── SMTP sender ──────────────────────────────────────────────────────────────

def send_smtp(html: str, chart_path: str) -> bool:
    """Send the report via SMTP (e.g. Gmail with App Password)."""
    msg = MIMEMultipart("related")
    msg["Subject"] = f"📦 Supply Chain KPI Report — {datetime.utcnow().strftime('%Y-%m-%d')}"
    msg["From"]    = EMAIL_USER
    msg["To"]      = EMAIL_TO

    alt = MIMEMultipart("alternative")
    msg.attach(alt)
    alt.attach(MIMEText(html, "html"))

    if Path(chart_path).exists():
        with open(chart_path, "rb") as f:
            img = MIMEImage(f.read())
        img.add_header("Content-ID", "<dashboard>")
        img.add_header("Content-Disposition", "inline", filename="kpi_dashboard.png")
        msg.attach(img)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, EMAIL_TO, msg.as_string())
        log.info("  ✉  Email sent to %s via SMTP", EMAIL_TO)
        return True
    except Exception as exc:
        log.error("  SMTP error: %s", exc)
        return False


# ── SendGrid sender ──────────────────────────────────────────────────────────

def send_sendgrid(html: str, chart_path: str) -> bool:
    """Send the report via SendGrid (free tier)."""
    try:
        import base64
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import (Mail, Attachment, FileContent,
                                           FileName, FileType, Disposition)

        message = Mail(
            from_email=EMAIL_USER,
            to_emails=EMAIL_TO,
            subject=f"📦 Supply Chain KPI Report — {datetime.utcnow().strftime('%Y-%m-%d')}",
            html_content=html,
        )
        if Path(chart_path).exists():
            with open(chart_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode()
            att = Attachment(
                FileContent(encoded),
                FileName("kpi_dashboard.png"),
                FileType("image/png"),
                Disposition("attachment"),
            )
            message.attachment = att

        sg = SendGridAPIClient(SENDGRID_KEY)
        response = sg.send(message)
        log.info("  ✉  Email sent via SendGrid (status %s)", response.status_code)
        return response.status_code in (200, 202)
    except Exception as exc:
        log.error("  SendGrid error: %s", exc)
        return False


# ── Main ─────────────────────────────────────────────────────────────────────

def send_report() -> bool:
    """Load KPIs and send the HTML report email."""
    if not KPI_JSON.exists():
        log.error("KPI JSON not found at %s — run pipeline.py first", KPI_JSON)
        return False

    with open(KPI_JSON) as f:
        kpis = json.load(f)

    html = build_html(kpis)

    if EMAIL_BACKEND == "sendgrid" and SENDGRID_KEY:
        return send_sendgrid(html, str(DASHBOARD_PNG))
    else:
        return send_smtp(html, str(DASHBOARD_PNG))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s | %(levelname)-8s | %(message)s")
    send_report()
