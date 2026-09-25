import os
import sys
import smtplib
import logging
from typing import List, Dict, Any, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

def safe_str(val, default: str = "") -> str:
    if val is None:
        return default
    return str(val).strip()

def safe_int(val, default: int = 587) -> int:
    if not val:
        return default
    try:
        return int(str(val).strip())
    except (ValueError, TypeError):
        return default

class Config:
    @classmethod
    def SMARTLEAD_API_KEY(cls) -> str:
        return safe_str(os.getenv("SMARTLEAD_API_KEY"), "6cb12a01-912e-4e93-a24b-3f146b7df3e2_wqqlhxf")

    @classmethod
    def CAMPAIGN_ID(cls) -> str:
        return safe_str(os.getenv("CAMPAIGN_ID"), "3921933")

    @classmethod
    def get_recipient_emails(cls) -> List[str]:
        raw = safe_str(
            os.getenv("RECIPIENT_EMAILS"),
            "tushar.mangla1120@gmail.com"
        )
        if not raw:
            return []
        return [email.strip() for email in raw.split(",") if email.strip()]

    @classmethod
    def SMTP_HOST(cls) -> str:
        return safe_str(os.getenv("SMTP_HOST"), "smtp.migadu.com")

    @classmethod
    def SMTP_PORT(cls) -> int:
        return safe_int(os.getenv("SMTP_PORT"), 465)

    @classmethod
    def SMTP_USER(cls) -> str:
        return safe_str(os.getenv("SMTP_USER"), "steven@smallgrp.agency")

    @classmethod
    def SMTP_PASSWORD(cls) -> str:
        return safe_str(os.getenv("SMTP_PASSWORD") or os.getenv("SMTP_PASS"), "Smallgrp@B8")

    @classmethod
    def SENDER_EMAIL(cls) -> str:
        return safe_str(os.getenv("SENDER_EMAIL") or os.getenv("SMTP_USER"), "steven@smallgrp.agency")

    @classmethod
    def SENDER_NAME(cls) -> str:
        return safe_str(os.getenv("SENDER_NAME"), "Smartlead Reply Notifier")

    @classmethod
    def WEBHOOK_SECRET(cls) -> str:
        return safe_str(os.getenv("WEBHOOK_SECRET"), "")

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
    lead_id: Optional[str] = None
) -> Dict[str, Any]:
    recipients = Config.get_recipient_emails()
    if not recipients:
        return {"status": "error", "message": "No recipients configured"}

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

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f4f6f9; padding: 20px; color: #1a1a1a;">
        <div style="max-width: 650px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e1e4e8; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.06);">
            <div style="background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%); color: #ffffff; padding: 24px;">
                <h2 style="margin: 0 0 6px 0; font-size: 20px; font-weight: 600;">📬 New Campaign Reply Received</h2>
                <p style="margin: 0; opacity: 0.9; font-size: 14px;">{campaign_title}</p>
            </div>
            <div style="padding: 24px;">
                <div style="margin-bottom: 20px;">
                    <p style="margin: 4px 0;"><strong>Lead Name:</strong> {lead_name}</p>
                    <p style="margin: 4px 0;"><strong>Lead Email:</strong> <a href="mailto:{lead_email}">{lead_email}</a></p>
                    {f'<p style="margin: 4px 0;"><strong>Campaign ID:</strong> {campaign_id}</p>' if campaign_id else ''}
                    {f'<p style="margin: 4px 0;"><strong>Received At:</strong> {reply_time}</p>' if reply_time else ''}
                </div>
                <div style="margin: 20px 0;">
                    <div style="font-size: 13px; font-weight: 700; color: #166534; text-transform: uppercase; margin-bottom: 6px;">💬 Latest Reply:</div>
                    <div style="background: #f0fdf4; border-left: 4px solid #22c55e; border-top: 1px solid #bbf7d0; border-right: 1px solid #bbf7d0; border-bottom: 1px solid #bbf7d0; padding: 16px; border-radius: 6px; font-size: 15px; color: #1e293b; white-space: pre-wrap;">{clean_reply_body}</div>
                </div>
                {f'<div style="margin-top: 16px;"><a href="{smartlead_lead_url}" style="display: inline-block; background-color: #4f46e5; color: #ffffff; text-decoration: none; padding: 12px 20px; border-radius: 8px; font-weight: 600; font-size: 14px;" target="_blank">View Lead in Smartlead &rarr;</a></div>' if smartlead_lead_url else ''}
                {thread_html}
            </div>
            <div style="background: #f9fafb; padding: 16px 24px; text-align: center; font-size: 12px; color: #9ca3af; border-top: 1px solid #f3f4f6;">
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

Latest Reply:
----------------------------------------
{clean_reply_body}
----------------------------------------

Smartlead Link: {smartlead_lead_url or 'N/A'}
{thread_plain}
    """

    if not smtp_user or not smtp_password:
        return {"status": "error", "message": "SMTP credentials missing"}

    successful_sends = []
    failed_sends = []

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
        msg["To"] = ", ".join(recipients)

        msg.attach(MIMEText(plain_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        refused = server.sendmail(sender_email, recipients, msg.as_string())
        successful_sends = [r for r in recipients if r not in refused]
        failed_sends = [{"recipient": r, "error": str(refused[r])} for r in refused]

        try:
            server.quit()
        except Exception:
            pass
    except Exception as smtp_err:
        return {"status": "error", "message": f"SMTP Connection failed: {smtp_err}"}

    return {"status": "success", "successful_sends": successful_sends, "failed_sends": failed_sends}

def extract_payload_data(payload: dict) -> dict:
    data = payload.get("data", payload) if isinstance(payload, dict) else {}
    lead = data.get("lead", {}) if isinstance(data, dict) and isinstance(data.get("lead"), dict) else {}
    reply = data.get("reply", {}) if isinstance(data, dict) and isinstance(data.get("reply"), dict) else {}

    raw_campaign_id = (
        data.get("campaign_id")
        or payload.get("campaign_id")
        or data.get("campaignId")
        or data.get("email_campaign_id")
        or payload.get("email_campaign_id")
    )
    campaign_id = str(raw_campaign_id).strip() if raw_campaign_id is not None else ""
    campaign_name = data.get("campaign_name") or payload.get("campaign_name") or data.get("campaignName")

    # Smartlead EMAIL_REPLY can put lead email in to_email, lead.email, lead_email, or from_email
    lead_email = (
        lead.get("email")
        or data.get("lead_email")
        or data.get("to_email")
        or payload.get("lead_email")
        or payload.get("to_email")
        or data.get("from_email")
        or payload.get("from_email")
        or data.get("email")
    )

    lead_first_name = (
        lead.get("first_name")
        or data.get("lead_first_name")
        or data.get("to_name")
        or data.get("first_name")
    )
    lead_last_name = (
        lead.get("last_name")
        or data.get("lead_last_name")
        or data.get("last_name")
    )

    reply_body = (
        reply.get("body")
        or reply.get("text")
        or data.get("reply_text")
        or data.get("reply_body")
        or data.get("text")
        or data.get("body")
        or data.get("email_body")
        or payload.get("reply_text")
        or payload.get("body")
    )

    reply_time = (
        reply.get("received_at")
        or data.get("sent_time")
        or data.get("timestamp")
        or data.get("created_at")
        or payload.get("sent_time")
        or payload.get("timestamp")
    )

    lead_id = data.get("lead_id") or payload.get("lead_id") or lead.get("id")
    smartlead_lead_url = (
        data.get("sl_lead_url")
        or data.get("lead_url")
        or data.get("url")
        or payload.get("sl_lead_url")
        or (f"https://app.smartlead.ai/app/campaigns/lead-details?lead_id={lead_id}" if lead_id else "")
    )

    return {
        "campaign_id": campaign_id,
        "campaign_name": campaign_name,
        "lead_email": lead_email,
        "lead_first_name": lead_first_name,
        "lead_last_name": lead_last_name,
        "reply_body": reply_body,
        "reply_time": reply_time,
        "smartlead_lead_url": smartlead_lead_url,
        "lead_id": lead_id
    }

@app.route("/", methods=["GET"])
@app.route("/api", methods=["GET"])
@app.route("/api/index", methods=["GET"])
def health_check():
    recipients = Config.get_recipient_emails()
    target_campaign = Config.CAMPAIGN_ID() or "(All campaigns)"
    return jsonify({
        "status": "online",
        "service": "Smartlead Reply Email Notifier",
        "target_campaign_id": target_campaign,
        "recipient_count": len(recipients),
        "recipients": recipients
    }), 200

@app.route("/webhook/smartlead", methods=["GET", "POST"])
@app.route("/api/webhook/smartlead", methods=["GET", "POST"])
def smartlead_webhook():
    if request.method == "GET":
        return jsonify({"status": "online", "message": "Smartlead Webhook Endpoint Ready"}), 200

    secret = Config.WEBHOOK_SECRET()
    if secret:
        token = request.headers.get("X-Webhook-Secret") or request.args.get("secret")
        if token != secret:
            return jsonify({"status": "error", "message": "Unauthorized"}), 401

    payload = request.get_json(silent=True) or {}
    extracted = extract_payload_data(payload)

    incoming_campaign_id = extracted["campaign_id"]
    lead_email = extracted["lead_email"]
    target_campaign_id = Config.CAMPAIGN_ID()

    if target_campaign_id and target_campaign_id != "*":
        allowed_campaign_ids = [c.strip() for c in target_campaign_id.split(",") if c.strip()]
        if incoming_campaign_id and incoming_campaign_id not in allowed_campaign_ids:
            return jsonify({
                "status": "ignored",
                "message": f"Campaign ID {incoming_campaign_id} does not match targeted campaign(s): {target_campaign_id}"
            }), 200

    if not lead_email:
        return jsonify({"status": "ignored", "message": "No lead email in payload"}), 200

    result = send_reply_notification(
        lead_email=lead_email,
        lead_first_name=extracted["lead_first_name"],
        lead_last_name=extracted["lead_last_name"],
        campaign_name=extracted["campaign_name"],
        campaign_id=incoming_campaign_id,
        reply_body=extracted["reply_body"],
        reply_time=extracted["reply_time"],
        smartlead_lead_url=extracted["smartlead_lead_url"],
        lead_id=extracted.get("lead_id")
    )

    return jsonify({"status": "processed", "notification_result": result}), 200

# Vercel entrypoint export
handler = app
