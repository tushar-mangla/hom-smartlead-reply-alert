import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
from config import Config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def send_reply_notification(
    lead_email: str,
    lead_first_name: Optional[str] = None,
    lead_last_name: Optional[str] = None,
    campaign_name: Optional[str] = None,
    campaign_id: Optional[str] = None,
    reply_body: Optional[str] = None,
    reply_time: Optional[str] = None,
    smartlead_lead_url: Optional[str] = None,
    additional_payload: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Sends notification email to all recipients listed in Config.get_recipient_emails().
    """
    recipients = Config.get_recipient_emails()
    if not recipients:
        logger.warning("No recipient emails configured in RECIPIENT_EMAILS env variable.")
        return {"status": "error", "message": "No recipients configured"}

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
    """

    # Check if SMTP configuration is set
    if not smtp_user or not smtp_password:
        logger.error("SMTP_USER or SMTP_PASSWORD not set in environment.")
        return {
            "status": "error",
            "message": "SMTP credentials missing in environment (.env or Vercel). Please set SMTP_USER and SMTP_PASSWORD.",
            "recipients_attempted": recipients,
        }

    successful_sends = []
    failed_sends = []

    try:
        # Establish SMTP connection
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
                logger.info(f"Successfully sent reply notification to {recipient}")
            except Exception as send_err:
                logger.error(f"Failed sending notification to {recipient}: {send_err}")
                failed_sends.append({"recipient": recipient, "error": str(send_err)})

        server.quit()
    except Exception as smtp_err:
        logger.error(f"SMTP Connection/Auth Error: {smtp_err}")
        return {
            "status": "error",
            "message": f"SMTP Connection failed: {smtp_err}",
            "successful": [],
            "failed": recipients
        }

    return {
        "status": "success" if successful_sends else "failed",
        "successful_sends": successful_sends,
        "failed_sends": failed_sends
    }
