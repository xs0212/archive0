from django.conf import settings
from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework import serializers
from core.authentication import generate_jwt
from .mfa import enroll, verify
from .models import User


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()
    otp = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        user = authenticate(username=attrs["username"], password=attrs["password"])
        if not user:
            raise serializers.ValidationError("invalid_credentials")
        if not user.is_active:
            raise serializers.ValidationError("inactive_user")
        attrs["user"] = user
        return attrs

    def create(self, validated_data):
        user = validated_data["user"]
        otp = validated_data.get("otp")
        requires_mfa = user.roles.filter(name__in=settings.MFA_SETTINGS["STEP_UP_ROLES"]).exists()
        mfa_verified_until = None
        if requires_mfa:
            if not hasattr(user, "mfa_secret"):
                return {"mfa_required": True, "reason": "not_enrolled"}
            if not otp:
                return {"mfa_required": True}
            if not verify(user, otp):
                raise serializers.ValidationError("invalid_otp")
            mfa_verified_until = timezone.now() + timezone.timedelta(
                minutes=settings.MFA_SETTINGS["SESSION_TTL_MINUTES"]
            )
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])
        token = generate_jwt(user, mfa_verified_until=mfa_verified_until)
        return {"token": token, "mfa_required": False}


class MfaEnrollSerializer(serializers.Serializer):
    def create(self, validated_data):
        request = self.context["request"]
        return {"provisioning_uri": enroll(request.user)}


class MfaVerifySerializer(serializers.Serializer):
    otp = serializers.CharField()

    def create(self, validated_data):
        user = self.context["request"].user
        if not verify(user, validated_data["otp"]):
            raise serializers.ValidationError("invalid_otp")
        mfa_verified_until = timezone.now() + timezone.timedelta(
            minutes=settings.MFA_SETTINGS["SESSION_TTL_MINUTES"]
        )
        token = generate_jwt(user, mfa_verified_until=mfa_verified_until)
        return {"token": token, "mfa_verified_until": mfa_verified_until}
