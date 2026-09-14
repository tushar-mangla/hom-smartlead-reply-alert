import sys
import requests
from config import Config

SMARTLEAD_BASE_URL = "https://server.smartlead.ai/api/v1"

def fetch_and_display_campaigns():
    api_key = Config.SMARTLEAD_API_KEY
    if not api_key:
        print("\n❌ Error: SMARTLEAD_API_KEY is not set in your .env file.")
        print("Please add SMARTLEAD_API_KEY=your_key to your .env file and try again.\n")
        sys.exit(1)

    url = f"{SMARTLEAD_BASE_URL}/campaigns"
    params = {"api_key": api_key}

    print(f"\n🔍 Fetching campaigns from Smartlead API...")
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            print(f"❌ API Error ({response.status_code}): {response.text}")
            sys.exit(1)

        campaigns = response.json()
        if not isinstance(campaigns, list):
            print(f"Unexpected response format: {campaigns}")
            sys.exit(1)

        if not campaigns:
            print("⚠️ No campaigns found in your Smartlead account.")
            return

        print("\n" + "=" * 80)
        print(f"{'CAMPAIGN ID':<15} | {'STATUS':<10} | {'REPLIES':<10} | {'CAMPAIGN NAME'}")
        print("=" * 80)

        for camp in campaigns:
            camp_id = str(camp.get("id", "N/A"))
            name = camp.get("name", "Unnamed Campaign")
            status = camp.get("status", "UNKNOWN")
            stats = camp.get("campaign_stat", {})
            replies = stats.get("reply_count", camp.get("replies_count", 0))

            print(f"{camp_id:<15} | {status:<10} | {replies:<10} | {name}")

        print("=" * 80)
        print("\n💡 Copy the desired CAMPAIGN ID and place it into your .env file:")
        print("   CAMPAIGN_ID=<selected_id>\n")

    except Exception as err:
        print(f"❌ Network or connection error: {err}")

if __name__ == "__main__":
    fetch_and_display_campaigns()
