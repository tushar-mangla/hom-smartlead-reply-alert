import os
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Smartlead settings
    SMARTLEAD_API_KEY: str = os.getenv("SMARTLEAD_API_KEY", "")
    # Target campaign ID to monitor (can be single ID or comma-separated, or '*' for all)
    CAMPAIGN_ID: str = os.getenv("CAMPAIGN_ID", "").strip()

    # Recipient emails (comma-separated list)
    RECIPIENT_EMAILS_RAW: str = os.getenv("RECIPIENT_EMAILS", "")
    
    @classmethod
    def get_recipient_emails(cls) -> List[str]:
        if not cls.RECIPIENT_EMAILS_RAW:
            return []
        return [email.strip() for email in cls.RECIPIENT_EMAILS_RAW.split(",") if email.strip()]

    # SMTP Configuration (for sending emails)
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", os.getenv("SMTP_PASS", ""))
    SENDER_EMAIL: str = os.getenv("SENDER_EMAIL", os.getenv("SMTP_USER", ""))
    SENDER_NAME: str = os.getenv("SENDER_NAME", "Smartlead Reply Alert")

    # Webhook server config
    WEBHOOK_PORT: int = int(os.getenv("WEBHOOK_PORT", "5000"))
    WEBHOOK_HOST: str = os.getenv("WEBHOOK_HOST", "0.0.0.0")
    WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "") # Optional secret token for verification
