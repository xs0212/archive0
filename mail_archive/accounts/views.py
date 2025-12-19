from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from core.authentication import generate_jwt
from audit.services import AuditService
from .serializers import LoginSerializer, MfaEnrollSerializer, MfaVerifySerializer
from .models import User


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.save()
        user = serializer.validated_data.get("user")
        AuditService.append(user, "LOGIN", {"mfa_required": data.get("mfa_required", False)})
        http_status = status.HTTP_200_OK if not data.get("mfa_required") else status.HTTP_202_ACCEPTED
        return Response(data, status=http_status)


class MfaEnrollView(APIView):
    def post(self, request):
        serializer = MfaEnrollSerializer(context={"request": request})
        data = serializer.save()
        AuditService.append(request.user, "MFA_ENROLL", {})
        return Response(data, status=status.HTTP_201_CREATED)


class MfaVerifyView(APIView):
    def post(self, request):
        serializer = MfaVerifySerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.save()
        AuditService.append(request.user, "MFA_VERIFY", {})
        return Response(data, status=status.HTTP_200_OK)


class CurrentUserView(APIView):
    def get(self, request):
        return Response(
            {
                "username": request.user.username,
                "email": request.user.email,
                "roles": request.user.role_codes,
                "department": request.user.department.path,
                "mfa_enrolled": hasattr(request.user, "mfa_secret"),
            }
        )
