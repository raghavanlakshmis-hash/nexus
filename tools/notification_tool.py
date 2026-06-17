import smtplib
import os
from email.mime.text import MIMEText
from twilio.rest import Client

def send_email_notification(to_email: str, subject: str, body: str) -> bool:
    """Send email via SMTP. Configure with Gmail app password."""
    try:
        # For demo: use Gmail SMTP
        # Add GMAIL_USER and GMAIL_APP_PASSWORD to .env
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = os.getenv("GMAIL_USER")
        msg["To"] = to_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(os.getenv("GMAIL_USER"), os.getenv("GMAIL_APP_PASSWORD"))
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Email send failed: {e}")
        return False

def send_sms_notification(to_phone: str, message: str) -> bool:
    """Send SMS via Twilio."""
    try:
        client = Client(
            os.getenv("TWILIO_ACCOUNT_SID"),
            os.getenv("TWILIO_AUTH_TOKEN")
        )
        client.messages.create(
            body=message,
            from_=os.getenv("TWILIO_PHONE_NUMBER"),
            to=to_phone
        )
        return True
    except Exception as e:
        print(f"SMS send failed: {e}")
        return False