from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from core.permissions import RBACPermission
from accounts.access import AccessService
from audit.services import AuditService
from .models import ArchivedEmail, ExportJob
from .serializers import ArchiveRequestSerializer, ArchivedEmailSerializer, ExportJobRequestSerializer
from .services import ArchiveIngestService, EmailAccessService
from .tasks import build_export_archive


class ArchiveIngestView(APIView):
    permission_classes = [RBACPermission]
    required_permission = "ARCHIVE_STORE"

    def post(self, request):
        serializer = ArchiveRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = ArchiveIngestService()
        email = service.ingest(user=request.user, payload=serializer.validated_data)
        return Response({"id": email.id, "sha256": email.sha256}, status=status.HTTP_201_CREATED)


class EmailDetailView(APIView):
    permission_classes = [RBACPermission]
    required_permission = "EMAIL_VIEW"

    def get(self, request, email_id: int):
        email = get_object_or_404(ArchivedEmail, id=email_id)
        AccessService.ensure_email_access(request.user, email)
        AccessService.ensure_time_scope(request.user, email.received_at)
        serializer = ArchivedEmailSerializer(email)
        presign = EmailAccessService().presign(email)
        AuditService.append(request.user, "EMAIL_VIEW", {"email_id": email_id})
        return Response({"email": serializer.data, "download_url": presign})


class EmailVerifyView(APIView):
    permission_classes = [RBACPermission]
    required_permission = "EMAIL_VERIFY"

    def post(self, request, email_id: int):
        email = get_object_or_404(ArchivedEmail, id=email_id)
        AccessService.ensure_email_access(request.user, email)
        AccessService.ensure_time_scope(request.user, email.received_at)
        verified = EmailAccessService().verify(email)
        AuditService.append(request.user, "EMAIL_VERIFY", {"email_id": email_id, "result": verified})
        return Response({"verified": verified})


class ExportJobView(APIView):
    permission_classes = [RBACPermission]
    required_permission = "EXPORT_EMAIL"
    require_mfa = True

    def post(self, request):
        serializer = ExportJobRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        AccessService.ensure_mailbox_access(request.user, data["mailbox"])
        AccessService.ensure_time_scope(request.user, data["time_start"])
        job = ExportJob.objects.create(
            owner=request.user,
            mailbox=data["mailbox"],
            time_start=data["time_start"],
            time_end=data["time_end"],
        )
        build_export_archive.delay(job.id)
        AuditService.append(request.user, "EXPORT_REQUEST", {"job_id": job.id})
        return Response({"job_id": job.id}, status=status.HTTP_202_ACCEPTED)
