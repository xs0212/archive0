"""TOTP management."""
from __future__ import annotations

import base64
import os
import pyotp
from django.conf import settings
from django.utils import timezone
from .models import MfaSecret, User


def enroll(user: User) -> str:
    secret = base64.b32encode(os.urandom(20)).decode()
    MfaSecret.objects.update_or_create(
        user=user,
        defaults={"totp_secret": secret.encode(), "enrolled_at": timezone.now()},
    )
    issuer = settings.JWT_SETTINGS["ISSUER"]
    otp = pyotp.TOTP(secret)
    return otp.provisioning_uri(name=user.email, issuer_name=f"{issuer} Mail Archive")


def verify(user: User, otp_code: str) -> bool:
    record = getattr(user, "mfa_secret", None)
    if not record:
        return False
    totp = pyotp.TOTP(record.totp_secret.decode())
    return totp.verify(otp_code, valid_window=1)
