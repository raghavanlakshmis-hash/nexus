import smtplib
import os
from email.mime.text import MIMEText
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException


def send_email_notification(to_email: str, subject: str, body: str) -> bool:
    """Send email via SMTP. Configure with Gmail app password."""
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = os.getenv("GMAIL_USER")
        msg["To"] = to_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(os.getenv("GMAIL_USER"), os.getenv("GMAIL_APP_PASSWORD"))
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"[Notification] Email send failed: {e}")
        return False


def send_sms_notification(to_phone: str, message: str) -> bool:
    """Send SMS via Twilio. Returns False (non-fatal) on any failure."""
    from_number = os.getenv("TWILIO_PHONE_NUMBER", "")
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")

    if not all([from_number, account_sid, auth_token]):
        print("[Notification] SMS skipped — Twilio credentials not configured.")
        return False

    try:
        client = Client(account_sid, auth_token)
        client.messages.create(body=message, from_=from_number, to=to_phone)
        print(f"[Notification] SMS sent to {to_phone}")
        return True

    except TwilioRestException as e:
        if e.code == 21266:
            print(
                f"[Notification] SMS not sent — 'To' and 'From' numbers are the same ({to_phone}).\n"
                f"  The emergency contact phone number must be different from your Twilio number.\n"
                f"  Fix: update EMERGENCY_CONTACT_PHONE in .env to a real recipient number."
            )
        # Error 21659 — from-number country does not match to-number country.
        # Common on trial accounts sending to a different country.
        elif e.code == 21659:
            print(
                f"[Notification] SMS not sent (Twilio error 21659 — country mismatch).\n"
                f"  From: {from_number}  To: {to_phone}\n"
                f"  Your Twilio 'from' number is registered in a different country than "
                f"the recipient's number.\n"
                f"  Fix options:\n"
                f"    1. Buy a Twilio number in the recipient's country and set it as "
                f"TWILIO_PHONE_NUMBER in .env\n"
                f"    2. Enable international SMS in the Twilio console under "
                f"'Messaging > Settings > Geo Permissions'\n"
                f"    3. Upgrade from a Twilio trial account (trial restricts "
                f"international sending)"
            )
        else:
            print(f"[Notification] SMS failed — Twilio error {e.code}: {e.msg}")
        return False

    except Exception as e:
        print(f"[Notification] SMS send failed: {e}")
        return False