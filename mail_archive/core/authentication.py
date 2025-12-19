"""Custom JWT authentication with MFA claims."""
from __future__ import annotations

import datetime as dt
import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import authentication, exceptions

User = get_user_model()


class JWTAuthentication(authentication.BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        header = authentication.get_authorization_header(request).decode("utf-8")
        if not header or not header.startswith(self.keyword):
            return None
        token = header[len(self.keyword) :].strip()
        payload = decode_jwt(token)
        try:
            user = User.objects.get(id=payload["sub"], is_active=True)
        except User.DoesNotExist as exc:
            raise exceptions.AuthenticationFailed("invalid_user") from exc
        request.auth = payload
        return user, payload


def _jwt_keys():
    signing_key = settings.JWT_SETTINGS["SIGNING_KEY"]
    verifying_key = settings.JWT_SETTINGS.get("VERIFYING_KEY") or signing_key
    return signing_key, verifying_key


def generate_jwt(user, *, mfa_verified_until: dt.datetime | None = None) -> str:
    now = timezone.now()
    exp = now + dt.timedelta(minutes=settings.JWT_SETTINGS["EXP_MINUTES"])
    payload = {
        "iss": settings.JWT_SETTINGS["ISSUER"],
        "aud": settings.JWT_SETTINGS["AUDIENCE"],
        "sub": str(user.id),
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "username": user.username,
        "roles": user.role_codes,
        "mfa_verified": bool(mfa_verified_until and mfa_verified_until > now),
        "mfa_verified_until": int(mfa_verified_until.timestamp()) if mfa_verified_until else None,
    }
    signing_key, _ = _jwt_keys()
    return jwt.encode(payload, signing_key, algorithm="HS256")


def decode_jwt(token: str) -> dict:
    _, verifying_key = _jwt_keys()
    try:
        payload = jwt.decode(
            token,
            verifying_key,
            audience=settings.JWT_SETTINGS["AUDIENCE"],
            issuer=settings.JWT_SETTINGS["ISSUER"],
            algorithms=["HS256"],
        )
    except jwt.PyJWTError as exc:
        raise exceptions.AuthenticationFailed("invalid_token") from exc
    return payload
