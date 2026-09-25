import sys
import os
import logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify
from config import Config
from notifier import send_reply_notification

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

def extract_payload_data(payload: dict) -> dict:
    """
    Safely extracts key fields from diverse Smartlead webhook payload structures.
    """
    data = payload.get("data", payload) if isinstance(payload, dict) else {}
    lead = data.get("lead", {}) if isinstance(data, dict) and isinstance(data.get("lead"), dict) else {}
    reply = data.get("reply", {}) if isinstance(data, dict) and isinstance(data.get("reply"), dict) else {}

    # Extract Campaign ID
    raw_campaign_id = (
        data.get("campaign_id")
        or payload.get("campaign_id")
        or data.get("campaignId")
        or data.get("email_campaign_id")
        or payload.get("email_campaign_id")
    )
    campaign_id = str(raw_campaign_id).strip() if raw_campaign_id is not None else ""

    # Extract Campaign Name
    campaign_name = data.get("campaign_name") or payload.get("campaign_name") or data.get("campaignName")

    # Extract Lead Email (Smartlead EMAIL_REPLY can put lead email in to_email, lead.email, lead_email, or from_email)
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

    # Extract Lead Name
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

    # Extract Reply Text Content
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

    # Extract Timestamp
    reply_time = (
        reply.get("received_at")
        or data.get("sent_time")
        or data.get("timestamp")
        or data.get("created_at")
        or payload.get("sent_time")
        or payload.get("timestamp")
    )

    # Extract Lead URL
    lead_id = data.get("lead_id") or payload.get("lead_id") or lead.get("id")
    smartlead_lead_url = (
        data.get("sl_lead_url")
        or data.get("lead_url")
        or data.get("url")
        or payload.get("sl_lead_url")
        or (f"https://app.smartlead.ai/app/campaigns/lead-details?lead_id={lead_id}" if lead_id else "")
    )

    # Event type check if present
    event_type = data.get("event_type") or payload.get("event_type") or payload.get("type") or payload.get("event") or "EMAIL_REPLY"

    return {
        "campaign_id": campaign_id,
        "campaign_name": campaign_name,
        "lead_email": lead_email,
        "lead_first_name": lead_first_name,
        "lead_last_name": lead_last_name,
        "reply_body": reply_body,
        "reply_time": reply_time,
        "smartlead_lead_url": smartlead_lead_url,
        "lead_id": lead_id,
        "event_type": event_type
    }

@app.route("/", methods=["GET"])
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
def smartlead_webhook():
    """
    Webhook endpoint to receive POST events (and GET verification requests) from Smartlead.
    """
    if request.method == "GET":
        return jsonify({
            "status": "online",
            "message": "Smartlead Webhook Endpoint Ready"
        }), 200

    # Optional secret verification if configured
    secret = Config.WEBHOOK_SECRET()
    if secret:
        token = request.headers.get("X-Webhook-Secret") or request.args.get("secret")
        if token != secret:
            logger.warning("Unauthorized webhook request: Invalid secret token.")
            return jsonify({"status": "error", "message": "Unauthorized"}), 401

    payload = request.get_json(silent=True) or {}
    logger.info(f"Received webhook payload: {payload}")

    extracted = extract_payload_data(payload)

    incoming_campaign_id = extracted["campaign_id"]
    lead_email = extracted["lead_email"]
    target_campaign_id = Config.CAMPAIGN_ID()

    logger.info(f"Parsed Webhook -> Event: {extracted['event_type']}, Campaign ID: {incoming_campaign_id}, Lead: {lead_email}")

    # Campaign Filtering Logic
    if target_campaign_id and target_campaign_id != "*":
        allowed_campaign_ids = [c.strip() for c in target_campaign_id.split(",") if c.strip()]
        if incoming_campaign_id and incoming_campaign_id not in allowed_campaign_ids:
            logger.info(f"Skipping notification: Incoming campaign ID '{incoming_campaign_id}' does not match target '{target_campaign_id}'")
            return jsonify({
                "status": "ignored",
                "message": f"Campaign ID {incoming_campaign_id} does not match targeted campaign(s): {target_campaign_id}"
            }), 200

    if not lead_email:
        logger.warning("No lead email found in webhook payload.")
        return jsonify({"status": "ignored", "message": "No lead email in payload"}), 200

    # When testing, pass only tushar.mangla1120@gmail.com
    is_test = (
        request.args.get("test") in ["true", "1"]
        or payload.get("test") is True
        or request.headers.get("X-Test-Recipient") is not None
    )
    test_recipients = ["tushar.mangla1120@gmail.com"] if is_test else None

    # Dispatch Email Notifications
    result = send_reply_notification(
        lead_email=lead_email,
        lead_first_name=extracted["lead_first_name"],
        lead_last_name=extracted["lead_last_name"],
        campaign_name=extracted["campaign_name"],
        campaign_id=incoming_campaign_id,
        reply_body=extracted["reply_body"],
        reply_time=extracted["reply_time"],
        smartlead_lead_url=extracted["smartlead_lead_url"],
        lead_id=extracted.get("lead_id"),
        recipients=test_recipients,
        additional_payload=payload
    )

    return jsonify({
        "status": "processed",
        "notification_result": result
    }), 200

if __name__ == "__main__":
    host = Config.WEBHOOK_HOST()
    port = Config.WEBHOOK_PORT()
    logger.info(f"Starting Smartlead Webhook Listener on {host}:{port}")
    logger.info(f"Monitoring Campaign ID: {Config.CAMPAIGN_ID() or 'ALL'}")
    logger.info(f"Notifying Recipients: {Config.get_recipient_emails()}")
    app.run(host=host, port=port, debug=False)
