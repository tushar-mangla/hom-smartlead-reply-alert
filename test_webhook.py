import requests
import json
from config import Config

def send_test_webhook():
    vercel_url = "https://hom-smartlead-reply-alert.vercel.app/webhook/smartlead"
    target_campaign = Config.CAMPAIGN_ID() or "3921933"

    mock_payload = {
        "event_type": "EMAIL_REPLY",
        "campaign_id": target_campaign if target_campaign != "*" else "3921933",
        "campaign_name": "HOM Local Painter 08 Sep 2026",
        "from_email": "prospect.ceo@targetcompany.com",
        "lead_first_name": "Sarah",
        "lead_last_name": "Connor",
        "reply_text": "Hi Team,\n\nThanks for reaching out! We are interested in painting services and would love to see pricing details and discuss availability for a quick 15-min call this Thursday.\n\nBest regards,\nSarah",
        "sent_time": "2026-09-15 10:30:00 UTC",
        "sl_lead_url": "https://app.smartlead.ai/app/campaigns/lead-details?lead_id=987654",
        "test": True
    }

    print(f"\n🚀 Sending mock Smartlead reply webhook to Vercel: {vercel_url}")
    print(f"Payload Campaign ID: {mock_payload['campaign_id']}")
    print(f"Payload Lead Email: {mock_payload['from_email']}\n")

    headers = {"Content-Type": "application/json"}
    secret = Config.WEBHOOK_SECRET()
    if secret:
        headers["X-Webhook-Secret"] = secret

    try:
        response = requests.post(vercel_url, json=mock_payload, headers=headers, timeout=15)
        print(f"Status Code: {response.status_code}")
        print(f"Response Body:\n{json.dumps(response.json(), indent=2)}\n")
        if response.status_code == 200:
            print("✅ Test webhook delivered successfully!\n")
    except Exception as e:
        print(f"❌ Error during test request: {e}\n")

if __name__ == "__main__":
    send_test_webhook()
