"""Notification service placeholders.

CURE monitoring task calls these functions to send alerts/escalations.
"""


def send_sms_alert(phone_number: str, message: str) -> dict:
    """Placeholder for Twilio SMS integration used during offline escalation."""
    return {"channel": "sms", "to": phone_number, "queued": True, "message": message}


def send_push_alert(device_token: str, payload: dict) -> dict:
    """Placeholder for FCM push notifications to emergency contacts/users."""
    return {"channel": "push", "to": device_token, "queued": True, "payload": payload}


def send_email_alert(email: str, subject: str, html_body: str) -> dict:
    """Placeholder for escalation emails with incident context attachments."""
    return {"channel": "email", "to": email, "queued": True, "subject": subject}
