import os
import resend

resend.api_key = os.getenv("RESEND_API_KEY")

def send_verification_email(email: str, token: str):
    params = {
        "from": "onboarding@resend.dev",
        "to": email,
        "subject": "Verify your email address",
        "html": f"<p>Please click this link to verify your email address: <a href='{os.getenv('FRONTEND_URL')}/verify_email?token={token}'>Verify Email</a></p>",
    }
    resend.Emails.send(params)
