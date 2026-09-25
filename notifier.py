import re
import html
import requests
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
from config import Config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def html_to_plain(raw_html: str) -> str:
    if not raw_html:
        return ""
    text = re.sub(r'<br\s*\/?>', '\n', raw_html, flags=re.IGNORECASE)
    text = re.sub(r'<\/p>|<\/div>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    return re.sub(r'\n\s*\n+', '\n\n', text).strip()

def fetch_lead_thread(
    campaign_id: Optional[str] = None,
    lead_id: Optional[str] = None,
    lead_email: Optional[str] = None
) -> List[Dict[str, Any]]:
    api_key = Config.SMARTLEAD_API_KEY()
    if not api_key:
        return []

    # If lead_id is missing, look it up by lead_email
    if not lead_id and lead_email:
        try:
            r = requests.get(
                "https://server.smartlead.ai/api/v1/leads/",
                params={"api_key": api_key, "email": lead_email.strip()},
                timeout=8
            )
            if r.status_code == 200:
                data = r.json()
                lead_id = str(data.get("id")) if data.get("id") else None
        except Exception as e:
            logger.warning(f"Could not lookup lead by email for thread history: {e}")

    if not lead_id or not campaign_id:
        return []

    try:
        url = f"https://server.smartlead.ai/api/v1/campaigns/{campaign_id}/leads/{lead_id}/message-history"
        r = requests.get(url, params={"api_key": api_key}, timeout=8)
        if r.status_code == 200:
            data = r.json()
            history = data.get("history", []) if isinstance(data, dict) else []
            # Keep customer replies and sent campaign sequence emails
            return [m for m in history if m.get("type") in ["SENT", "REPLY"]]
    except Exception as e:
        logger.warning(f"Could not fetch message history: {e}")

    return []

def format_thread_html(thread: List[Dict[str, Any]]) -> str:
    if not thread:
        return ""
    cards = []
    for idx, msg in enumerate(thread, 1):
        m_type = msg.get("type", "").upper()
        time_str = msg.get("time", "")
        sender = msg.get("from", "")
        recipient = msg.get("to", "")
        subject = msg.get("subject") or ""
        seq = msg.get("email_seq_number")
        raw_body = msg.get("email_body") or ""
        clean_body = re.sub(r'<\/?(html|head|meta|body)[^>]*>', '', raw_body, flags=re.IGNORECASE).strip()

        if m_type == "REPLY":
            badge_bg = "#dcfce7"
            badge_color = "#15803d"
            badge_text = "📥 Lead Reply"
            card_border = "#22c55e"
            card_bg = "#f0fdf4"
        else:
            seq_label = f" (Step #{seq})" if seq else ""
            badge_bg = "#e0e7ff"
            badge_color = "#3730a3"
            badge_text = f"📤 Outbound Email{seq_label}"
            card_border = "#cbd5e1"
            card_bg = "#f8fafc"

        cards.append(f"""
        <div style="border: 1px solid {card_border}; border-radius: 8px; margin-bottom: 16px; background: {card_bg}; overflow: hidden;">
            <div style="padding: 10px 16px; background: #ffffff; border-bottom: 1px solid {card_border}; font-size: 12px; color: #64748b;">
                <span style="background: {badge_bg}; color: {badge_color}; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 10px; margin-right: 8px;">{badge_text}</span>
                <strong>From:</strong> {sender} &rarr; <strong>To:</strong> {recipient}
                <span style="float: right; color: #94a3b8;">{time_str}</span>
            </div>
            {f'<div style="padding: 8px 16px 0 16px; font-size: 13px; font-weight: 600; color: #334155;">Subject: {html.escape(subject)}</div>' if subject else ''}
            <div style="padding: 12px 16px; font-size: 14px; line-height: 1.5; color: #1e293b;">
                {clean_body}
            </div>
        </div>
        """)

    return f"""
    <div style="margin-top: 32px; border-top: 2px dashed #cbd5e1; padding-top: 24px;">
        <h3 style="font-size: 16px; color: #1e293b; margin: 0 0 16px 0; font-weight: 700;">
            📜 Full Email Conversation Thread ({len(thread)} message{'s' if len(thread) > 1 else ''})
        </h3>
        {''.join(cards)}
    </div>
    """

def format_thread_plain(thread: List[Dict[str, Any]]) -> str:
    if not thread:
        return ""
    lines = [
        "\n==================================================",
        f"📜 FULL EMAIL CONVERSATION THREAD ({len(thread)} messages):",
        "=================================================="
    ]
    for idx, msg in enumerate(thread, 1):
        m_type = msg.get("type", "").upper()
        time_str = msg.get("time", "")
        sender = msg.get("from", "")
        recipient = msg.get("to", "")
        subject = msg.get("subject") or "No Subject"
        seq = msg.get("email_seq_number")
        raw_body = msg.get("email_body") or ""
        body_text = html_to_plain(raw_body)
        tag = "📥 LEAD REPLY" if m_type == "REPLY" else f"📤 OUTBOUND (Step #{seq})"
        lines.append(f"\n--- [{idx}] {tag} ---")
        lines.append(f"Time: {time_str}")
        lines.append(f"From: {sender} -> To: {recipient}")
        if subject and subject != "No Subject":
            lines.append(f"Subject: {subject}")
        lines.append(f"\n{body_text}\n")
    lines.append("==================================================")
    return "\n".join(lines)

def send_reply_notification(
    lead_email: str,
    lead_first_name: Optional[str] = None,
    lead_last_name: Optional[str] = None,
    campaign_name: Optional[str] = None,
    campaign_id: Optional[str] = None,
    reply_body: Optional[str] = None,
    reply_time: Optional[str] = None,
    smartlead_lead_url: Optional[str] = None,
    lead_id: Optional[str] = None,
    recipients: Optional[List[str]] = None,
    additional_payload: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Sends notification email to all recipients listed in Config.get_recipient_emails(),
    including the latest reply and the entire email conversation thread.
    """
    active_recipients = recipients or Config.get_recipient_emails()
    if not active_recipients:
        logger.warning("No recipient emails configured in RECIPIENT_EMAILS env variable.")
        return {"status": "error", "message": "No recipients configured"}

    # Fetch full thread from Smartlead API
    thread = fetch_lead_thread(campaign_id=campaign_id, lead_id=lead_id, lead_email=lead_email)
    thread_html = format_thread_html(thread)
    thread_plain = format_thread_plain(thread)

    smtp_user = Config.SMTP_USER()
    smtp_password = Config.SMTP_PASSWORD()
    smtp_host = Config.SMTP_HOST()
    smtp_port = Config.SMTP_PORT()
    sender_email = Config.SENDER_EMAIL()
    sender_name = Config.SENDER_NAME()

    lead_name = f"{lead_first_name or ''} {lead_last_name or ''}".strip() or "Unknown Lead"
    campaign_title = campaign_name or (f"Campaign #{campaign_id}" if campaign_id else "Smartlead Campaign")
    clean_reply_body = (reply_body or "No text content provided").strip()

    subject = f"🚨 New Reply on {campaign_title}: {lead_name} ({lead_email})"

    # Construct HTML email body with modern styling
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                background-color: #f4f6f9;
                margin: 0;
                padding: 20px;
                color: #1a1a1a;
            }}
            .card {{
                max-width: 600px;
                margin: 0 auto;
                background: #ffffff;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
                overflow: hidden;
                border: 1px solid #e1e4e8;
            }}
            .header {{
                background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%);
                color: #ffffff;
                padding: 24px;
                text-align: left;
            }}
            .header h2 {{
                margin: 0 0 6px 0;
                font-size: 20px;
                font-weight: 600;
            }}
            .header p {{
                margin: 0;
                opacity: 0.9;
                font-size: 14px;
            }}
            .content {{
                padding: 24px;
            }}
            .info-grid {{
                display: table;
                width: 100%;
                margin-bottom: 20px;
            }}
            .info-row {{
                display: table-row;
            }}
            .info-label {{
                display: table-cell;
                padding: 6px 12px 6px 0;
                font-weight: 600;
                color: #6b7280;
                font-size: 13px;
                width: 120px;
            }}
            .info-value {{
                display: table-cell;
                padding: 6px 0;
                color: #111827;
                font-size: 14px;
            }}
            .reply-box {{
                background: #f8fafc;
                border-left: 4px solid #4f46e5;
                padding: 16px;
                border-radius: 6px;
                margin: 20px 0;
                font-size: 15px;
                line-height: 1.6;
                white-space: pre-wrap;
                color: #1e293b;
            }}
            .button {{
                display: inline-block;
                background-color: #4f46e5;
                color: #ffffff !important;
                text-decoration: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: 600;
                font-size: 14px;
                margin-top: 12px;
            }}
            .footer {{
                background: #f9fafb;
                padding: 16px 24px;
                text-align: center;
                font-size: 12px;
                color: #9ca3af;
                border-top: 1px solid #f3f4f6;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="header">
                <h2>📬 New Campaign Reply Received</h2>
                <p>{campaign_title}</p>
            </div>
            <div class="content">
                <div class="info-grid">
                    <div class="info-row">
                        <div class="info-label">Lead Name:</div>
                        <div class="info-value"><strong>{lead_name}</strong></div>
                    </div>
                    <div class="info-row">
                        <div class="info-label">Lead Email:</div>
                        <div class="info-value"><a href="mailto:{lead_email}">{lead_email}</a></div>
                    </div>
                    {f'<div class="info-row"><div class="info-label">Campaign ID:</div><div class="info-value">{campaign_id}</div></div>' if campaign_id else ''}
                    {f'<div class="info-row"><div class="info-label">Received At:</div><div class="info-value">{reply_time}</div></div>' if reply_time else ''}
                </div>

                <div style="font-weight: 600; color: #374151; font-size: 14px;">Reply Content:</div>
                <div class="reply-box">{clean_reply_body}</div>

                {f'<a href="{smartlead_lead_url}" class="button" target="_blank">View Lead in Smartlead &rarr;</a>' if smartlead_lead_url else ''}
                {thread_html}
            </div>
            <div class="footer">
                Automated alert sent by Smartlead Reply Notifier
            </div>
        </div>
    </body>
    </html>
    """

    plain_body = f"""
New Reply Received for Campaign: {campaign_title}

Lead Name: {lead_name}
Lead Email: {lead_email}
Campaign ID: {campaign_id or 'N/A'}
Received At: {reply_time or 'N/A'}

Reply Text:
----------------------------------------
{clean_reply_body}
----------------------------------------

Smartlead Link: {smartlead_lead_url or 'N/A'}
{thread_plain}
    """

    # Check if SMTP configuration is set
    if not smtp_user or not smtp_password:
        logger.error("SMTP_USER or SMTP_PASSWORD not set in environment.")
        return {
            "status": "error",
            "message": "SMTP credentials missing in environment (.env or Vercel). Please set SMTP_USER and SMTP_PASSWORD.",
            "recipients_attempted": active_recipients,
        }

    try:
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=20)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=20)
            server.starttls()

        server.login(smtp_user, smtp_password)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{sender_name} <{sender_email}>"
        msg["To"] = ", ".join(active_recipients)

        msg.attach(MIMEText(plain_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        refused = server.sendmail(sender_email, active_recipients, msg.as_string())
        successful_sends = [r for r in active_recipients if r not in refused]
        failed_sends = [{"recipient": r, "error": str(refused[r])} for r in refused]

        try:
            server.quit()
        except Exception:
            pass
    except Exception as smtp_err:
        logger.error(f"SMTP Connection/Auth Error: {smtp_err}")
        return {
            "status": "error",
            "message": f"SMTP Connection failed: {smtp_err}",
            "successful": [],
            "failed": active_recipients
        }

    return {
        "status": "success" if successful_sends else "failed",
        "successful_sends": successful_sends,
        "failed_sends": failed_sends
    }
