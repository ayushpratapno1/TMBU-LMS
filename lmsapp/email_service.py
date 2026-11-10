import os
import secrets
import logging
from django.conf import settings
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

def generate_otp(length=6):
    """Generate a cryptographically secure numeric OTP."""
    return "".join(str(secrets.randbelow(10)) for _ in range(length))

def mask_email(email):
    """Mask email for privacy, e.g. ay***1@gmail.com."""
    if not email or "@" not in email:
        return email or "registered email"
    user_part, domain_part = email.split("@", 1)
    if len(user_part) <= 2:
        masked_user = user_part[0] + "***"
    else:
        masked_user = user_part[:2] + "***" + user_part[-1]
    return f"{masked_user}@{domain_part}"

def get_admin_email(userid):
    """Get the registered email address for the admin user."""
    user = User.objects.filter(username=userid).first()
    if user and user.email:
        return user.email
    # Fallback to environment/superuser configuration
    return (
        os.environ.get('SUPERUSER_EMAIL')
        or os.environ.get('ADMIN_EMAIL')
        or getattr(settings, 'SUPERUSER_EMAIL', None)
    )

def send_otp_email(to_email, otp):
    """
    Send a 6-digit OTP email using Resend service.
    Returns (success: bool, error_message: str | None).
    """
    api_key = getattr(settings, 'RESEND_API_KEY', '') or os.environ.get('RESEND_API_KEY', '')
    from_email = getattr(settings, 'RESEND_FROM_EMAIL', '') or os.environ.get('RESEND_FROM_EMAIL', 'onboarding@resend.dev')

    subject = "LMS Admin Login - Your 2FA Verification Code"
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>LMS Admin 2FA Code</title>
    </head>
    <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px;">
        <div style="max-width: 520px; margin: 20px auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.08); border: 1px solid #e1e4e8;">
            <div style="background: linear-gradient(135deg, #1f2937, #111827); padding: 24px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 22px; letter-spacing: 1px;">Library Management System</h1>
                <p style="color: #9ca3af; margin: 5px 0 0 0; font-size: 13px;">Administrator 2-Factor Authentication</p>
            </div>
            <div style="padding: 30px 25px;">
                <p style="font-size: 15px; color: #374151; margin-top: 0;">Hello <strong>Admin</strong>,</p>
                <p style="font-size: 14px; color: #4b5563; line-height: 1.5;">
                    A login attempt was made for your administrator account. Please use the following One-Time Password (OTP) to complete your 2-Factor Authentication:
                </p>
                
                <div style="text-align: center; margin: 28px 0;">
                    <div style="display: inline-block; font-size: 32px; font-weight: 700; letter-spacing: 8px; color: #1e40af; background-color: #eff6ff; padding: 14px 28px; border-radius: 8px; border: 2px dashed #93c5fd;">
                        {otp}
                    </div>
                </div>

                <p style="font-size: 13px; color: #6b7280; text-align: center; margin-bottom: 24px;">
                    ⏱️ This OTP is valid for <strong>5 minutes</strong>.
                </p>

                <div style="background-color: #fef2f2; border-left: 4px solid #ef4444; padding: 12px 16px; border-radius: 4px;">
                    <p style="margin: 0; font-size: 12px; color: #991b1b;">
                        <strong>Security Notice:</strong> Never share this OTP with anyone. If you did not initiate this login request, please secure your account credentials immediately.
                    </p>
                </div>
            </div>
            <div style="background-color: #f9fafb; padding: 16px; text-align: center; border-top: 1px solid #e5e7eb;">
                <p style="margin: 0; font-size: 12px; color: #9ca3af;">
                    &copy; Library Management System &bull; Automated Security Service
                </p>
            </div>
        </div>
    </body>
    </html>
    """

    if not api_key:
        logger.warning(f"RESEND_API_KEY is not set. OTP for {to_email} is: {otp}")
        print(f"\n==========================================")
        print(f"[2FA OTP NOTICE] RESEND_API_KEY not configured in environment.")
        print(f"Recipient: {to_email}")
        print(f"OTP Code : {otp}")
        print(f"==========================================\n")
        return True, None

    try:
        import resend
        resend.api_key = api_key
        params = {
            "from": from_email,
            "to": [to_email],
            "subject": subject,
            "html": html_content,
        }
        resend.Emails.send(params)
        return True, None
    except Exception as e:
        logger.error(f"Failed to send OTP email via Resend to {to_email}: {e}")
        if getattr(settings, 'DEBUG', False):
            print(f"\n[DEBUG 2FA OTP FALLBACK] Resend error: {e}. OTP for {to_email} is: {otp}\n")
        return False, str(e)

