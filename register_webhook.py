import sys
import requests
from config import Config

SMARTLEAD_BASE_URL = "https://server.smartlead.ai/api/v1"

def register_webhook_in_smartlead(webhook_url: str, campaign_id: str = None):
    api_key = Config.SMARTLEAD_API_KEY()
    target_campaign_id = campaign_id or Config.CAMPAIGN_ID()

    if not api_key:
        print("❌ Error: SMARTLEAD_API_KEY is missing in your .env file.")
        sys.exit(1)

    if not webhook_url:
        print("❌ Error: Please provide your public webhook URL (e.g. ngrok or server URL).")
        print("Usage: python register_webhook.py https://your-domain.ngrok-free.app/webhook/smartlead")
        sys.exit(1)

    # Smartlead campaign-level webhook endpoint
    if target_campaign_id and target_campaign_id != "*":
        endpoint = f"{SMARTLEAD_BASE_URL}/campaigns/{target_campaign_id}/webhooks"
        print(f"\n📡 Registering webhook for Campaign ID: {target_campaign_id}...")
    else:
        endpoint = f"{SMARTLEAD_BASE_URL}/webhooks"
        print(f"\n📡 Registering global account-level webhook...")

    params = {"api_key": api_key}
    payload = {
        "name": "Reply Alert Notifier",
        "webhook_url": webhook_url,
        "event_types": ["EMAIL_REPLY"]
    }

    try:
        response = requests.post(endpoint, params=params, json=payload, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code in [200, 201]:
            print("✅ Success! Webhook registered successfully in Smartlead.")
            print(f"Webhook URL: {webhook_url}")
            print(f"Events: EMAIL_REPLY\n")
        else:
            print(f"⚠️ Response: {response.text}")
            print("\nIf campaign API registration requires UI setup, follow the Dashboard UI steps in the guide.\n")
    except Exception as err:
        print(f"❌ Error connecting to Smartlead API: {err}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("Enter your public Webhook URL (e.g. https://xxxx.ngrok-free.app/webhook/smartlead): ").strip()
    
    register_webhook_in_smartlead(url)
