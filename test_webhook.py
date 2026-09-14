import requests
import json
from config import Config

def send_test_webhook():
    port = Config.WEBHOOK_PORT or 5000
    webhook_url = f"http://127.0.0.1:{port}/webhook/smartlead"
    target_campaign = Config.CAMPAIGN_ID or "123456"

    # Simulated Smartlead webhook payload for a reply
    mock_payload = {
        "event_type": "EMAIL_REPLY",
        "campaign_id": target_campaign if target_campaign != "*" else "123456",
        "campaign_name": "Q3 Enterprise Outreach Campaign",
        "from_email": "prospect.ceo@targetcompany.com",
        "lead_first_name": "Sarah",
        "lead_last_name": "Connor",
        "reply_text": "Hi Team,\n\nThanks for reaching out. We are actually interested in your solution. Can you share pricing details and your availability for a quick 15-min call this Thursday?\n\nBest regards,\nSarah",
        "sent_time": "2026-09-15 10:30:00 UTC",
        "sl_lead_url": "https://app.smartlead.ai/app/campaigns/lead-details?lead_id=987654"
    }

    print(f"\n🚀 Sending mock Smartlead reply webhook to: {webhook_url}")
    print(f"Payload Campaign ID: {mock_payload['campaign_id']}")
    print(f"Payload Lead Email: {mock_payload['from_email']}\n")

    headers = {"Content-Type": "application/json"}
    if Config.WEBHOOK_SECRET:
        headers["X-Webhook-Secret"] = Config.WEBHOOK_SECRET

    try:
        response = requests.post(webhook_url, json=mock_payload, headers=headers, timeout=10)
        print(f"Response Status Code: {response.status_code}")
        print(f"Response Body:\n{json.dumps(response.json(), indent=2)}\n")
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection Error: Is the server running on port {port}? Start it first with: python server.py\n")
    except Exception as e:
        print(f"❌ Error during test request: {e}\n")

if __name__ == "__main__":
    send_test_webhook()
