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
        return safe_str(os.getenv("SMARTLEAD_API_KEY"), "")

    @classmethod
    def CAMPAIGN_ID(cls) -> str:
        return safe_str(os.getenv("CAMPAIGN_ID"), "")

    @classmethod
    def get_recipient_emails(cls) -> List[str]:
        raw = safe_str(os.getenv("RECIPIENT_EMAILS"), "")
        if not raw:
            return []
        return [email.strip() for email in raw.split(",") if email.strip()]

    @classmethod
    def SMTP_HOST(cls) -> str:
        return safe_str(os.getenv("SMTP_HOST"), "smtp.gmail.com")

    @classmethod
    def SMTP_PORT(cls) -> int:
        return safe_int(os.getenv("SMTP_PORT"), 587)

    @classmethod
    def SMTP_USER(cls) -> str:
        return safe_str(os.getenv("SMTP_USER"), "")

    @classmethod
    def SMTP_PASSWORD(cls) -> str:
        return safe_str(os.getenv("SMTP_PASSWORD") or os.getenv("SMTP_PASS"), "")

    @classmethod
    def SENDER_EMAIL(cls) -> str:
        return safe_str(os.getenv("SENDER_EMAIL") or os.getenv("SMTP_USER"), "")

    @classmethod
    def SENDER_NAME(cls) -> str:
        return safe_str(os.getenv("SENDER_NAME"), "Smartlead Reply Alert")

    @classmethod
    def WEBHOOK_SECRET(cls) -> str:
        return safe_str(os.getenv("WEBHOOK_SECRET"), "")

def send_reply_notification(
    lead_email: str,
    lead_first_name: Optional[str] = None,
    lead_last_name: Optional[str] = None,
    campaign_name: Optional[str] = None,
    campaign_id: Optional[str] = None,
    reply_body: Optional[str] = None,
    reply_time: Optional[str] = None,
    smartlead_lead_url: Optional[str] = None
) -> Dict[str, Any]:
    recipients = Config.get_recipient_emails()
    if not recipients:
        return {"status": "error", "message": "No recipients configured in Vercel Environment Variables"}

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
    <body style="font-family: sans-serif; background-color: #f4f6f9; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background: #fff; border-radius: 12px; padding: 24px; border: 1px solid #e1e4e8;">
            <h2 style="color: #4f46e5; margin-top: 0;">📬 New Campaign Reply Received</h2>
            <p><strong>Campaign:</strong> {campaign_title}</p>
            <p><strong>Lead Name:</strong> {lead_name}</p>
            <p><strong>Lead Email:</strong> <a href="mailto:{lead_email}">{lead_email}</a></p>
            {f'<p><strong>Campaign ID:</strong> {campaign_id}</p>' if campaign_id else ''}
            {f'<p><strong>Received At:</strong> {reply_time}</p>' if reply_time else ''}
            <div style="background: #f8fafc; border-left: 4px solid #4f46e5; padding: 16px; margin: 20px 0; white-space: pre-wrap;">{clean_reply_body}</div>
            {f'<a href="{smartlead_lead_url}" style="background-color: #4f46e5; color: #fff; padding: 10px 20px; text-decoration: none; border-radius: 6px; display: inline-block;" target="_blank">View Lead in Smartlead &rarr;</a>' if smartlead_lead_url else ''}
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
    """

    if not smtp_user or not smtp_password:
        return {"status": "error", "message": "SMTP credentials missing in environment variables"}

    successful_sends = []
    failed_sends = []

    try:
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
            server.starttls()

        server.login(smtp_user, smtp_password)

        for recipient in recipients:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = f"{sender_name} <{sender_email}>"
                msg["To"] = recipient

                msg.attach(MIMEText(plain_body, "plain", "utf-8"))
                msg.attach(MIMEText(html_body, "html", "utf-8"))

                server.sendmail(sender_email, recipient, msg.as_string())
                successful_sends.append(recipient)
            except Exception as send_err:
                failed_sends.append({"recipient": recipient, "error": str(send_err)})

        server.quit()
    except Exception as smtp_err:
        return {"status": "error", "message": f"SMTP Connection failed: {smtp_err}"}

    return {"status": "success", "successful_sends": successful_sends, "failed_sends": failed_sends}

def extract_payload_data(payload: dict) -> dict:
    if not isinstance(payload, dict):
        payload = {}
    data = payload.get("data", payload) if isinstance(payload, dict) else {}
    if not isinstance(data, dict):
        data = {}
    lead = data.get("lead", {}) if isinstance(data, dict) else {}
    if not isinstance(lead, dict):
        lead = {}

    raw_campaign_id = data.get("campaign_id") or payload.get("campaign_id") or data.get("campaignId")
    campaign_id = str(raw_campaign_id).strip() if raw_campaign_id is not None else ""
    campaign_name = data.get("campaign_name") or payload.get("campaign_name") or data.get("campaignName")

    lead_email = (
        data.get("from_email")
        or data.get("lead_email")
        or lead.get("email")
        or data.get("email")
        or payload.get("from_email")
    )

    lead_first_name = data.get("lead_first_name") or lead.get("first_name") or data.get("first_name")
    lead_last_name = data.get("lead_last_name") or lead.get("last_name") or data.get("last_name")

    reply_body = (
        data.get("reply_text")
        or data.get("reply_body")
        or data.get("text")
        or data.get("body")
        or data.get("email_body")
        or payload.get("reply_text")
    )

    reply_time = data.get("sent_time") or data.get("timestamp") or data.get("created_at") or payload.get("sent_time")
    smartlead_lead_url = data.get("sl_lead_url") or data.get("lead_url") or data.get("url") or payload.get("sl_lead_url")

    return {
        "campaign_id": campaign_id,
        "campaign_name": campaign_name,
        "lead_email": lead_email,
        "lead_first_name": lead_first_name,
        "lead_last_name": lead_last_name,
        "reply_body": reply_body,
        "reply_time": reply_time,
        "smartlead_lead_url": smartlead_lead_url
    }

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'OPTIONS'])
@app.route('/<path:path>', methods=['GET', 'POST', 'OPTIONS'])
def catch_all(path=""):
    try:
        if request.method == "GET":
            recipients = Config.get_recipient_emails()
            target_campaign = Config.CAMPAIGN_ID() or "(All campaigns)"
            return jsonify({
                "status": "online",
                "service": "Smartlead Reply Email Notifier",
                "target_campaign_id": target_campaign,
                "recipient_count": len(recipients),
                "recipients": recipients
            }), 200

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
                    "message": f"Campaign ID '{incoming_campaign_id}' does not match targeted campaign(s): {target_campaign_id}"
                }), 200

        if not lead_email:
            return jsonify({"status": "received", "message": "Webhook ping received (no lead email provided)"}), 200

        result = send_reply_notification(
            lead_email=lead_email,
            lead_first_name=extracted["lead_first_name"],
            lead_last_name=extracted["lead_last_name"],
            campaign_name=extracted["campaign_name"],
            campaign_id=incoming_campaign_id,
            reply_body=extracted["reply_body"],
            reply_time=extracted["reply_time"],
            smartlead_lead_url=extracted["smartlead_lead_url"]
        )

        return jsonify({"status": "processed", "notification_result": result}), 200
    except Exception as err:
        logger.error(f"Error handling webhook: {err}")
        return jsonify({"status": "error", "error": str(err)}), 200

# Vercel entrypoint export
handler = app
