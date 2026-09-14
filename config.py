import os
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

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
    def WEBHOOK_PORT(cls) -> int:
        return safe_int(os.getenv("WEBHOOK_PORT"), 5000)

    @classmethod
    def WEBHOOK_HOST(cls) -> str:
        return safe_str(os.getenv("WEBHOOK_HOST"), "0.0.0.0")

    @classmethod
    def WEBHOOK_SECRET(cls) -> str:
        return safe_str(os.getenv("WEBHOOK_SECRET"), "")
