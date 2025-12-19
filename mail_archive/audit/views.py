from rest_framework.generics import ListAPIView
from rest_framework.pagination import LimitOffsetPagination
from core.permissions import RBACPermission
from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogView(ListAPIView):
    serializer_class = AuditLogSerializer
    queryset = AuditLog.objects.all()
    pagination_class = LimitOffsetPagination
    permission_classes = [RBACPermission]
    required_permission = "AUDIT_READ"
    require_mfa = True

    def get_queryset(self):
        qs = super().get_queryset()
        actor = self.request.query_params.get("actor")
        action = self.request.query_params.get("action")
        if actor:
            qs = qs.filter(actor_id=actor)
        if action:
            qs = qs.filter(action=action)
        return qs
