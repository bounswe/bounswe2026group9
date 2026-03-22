import secrets
import smtplib
from datetime import UTC, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings
from app.database import get_supabase


def is_smtp_configured() -> bool:
    return all([settings.SMTP_HOST, settings.SMTP_USER, settings.SMTP_PASSWORD])


def generate_verification_token() -> str:
    return secrets.token_urlsafe(32)


def store_verification_token(user_id: str, token: str) -> None:
    db = get_supabase()
    # Delete any existing tokens for this user
    db.table("email_verification_tokens").delete().eq("user_id", user_id).execute()
    # Insert new token (24h expiry)
    expires_at = datetime.now(UTC) + timedelta(hours=24)
    db.table("email_verification_tokens").insert({
        "user_id": user_id,
        "token": token,
        "expires_at": expires_at.isoformat(),
    }).execute()


def validate_verification_token(token: str) -> str | None:
    """Returns user_id if token is valid, None otherwise."""
    db = get_supabase()
    result = (
        db.table("email_verification_tokens")
        .select("user_id, expires_at")
        .eq("token", token)
        .execute()
    )
    if not result.data:
        return None
    row = result.data[0]
    if datetime.fromisoformat(row["expires_at"]) < datetime.now(UTC):
        return None
    return row["user_id"]


def delete_verification_token(token: str) -> None:
    db = get_supabase()
    db.table("email_verification_tokens").delete().eq("token", token).execute()


def mark_email_verified(user_id: str) -> None:
    db = get_supabase()
    db.table("users").update({"email_verified": True}).eq("id", user_id).execute()


def send_verification_email(to_email: str, token: str) -> bool:
    """Send verification email. Returns True on success, False on failure."""
    if not is_smtp_configured():
        if not settings.is_production:
            print(f"[EMAIL] SMTP not configured. Verification token: {token}")
        else:
            print("[EMAIL] SMTP not configured. Cannot send verification email.")
        return False

    verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
        <h2 style="color: #1a1a1a;">Email Adresini Onayla</h2>
        <p style="color: #444; line-height: 1.6;">
            Social Event Mapper'a hoş geldin! Hesabını aktifleştirmek için
            aşağıdaki butona tıkla.
        </p>
        <a href="{verify_url}"
           style="display: inline-block; background: #4F46E5; color: #fff;
                  padding: 12px 32px; border-radius: 6px; text-decoration: none;
                  margin: 24px 0; font-weight: bold;">
            Email Adresimi Onayla
        </a>
        <p style="color: #888; font-size: 13px;">
            Bu link 24 saat geçerlidir. Eğer bu hesabı sen oluşturmadıysan bu maili görmezden gelebilirsin.
        </p>
    </div>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Email Adresini Onayla — Social Event Mapper"
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_EMAIL, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"[EMAIL] Failed to send: {e}")
        return False
