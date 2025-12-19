from rest_framework import serializers
from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = [
            "id",
            "actor",
            "actor_role",
            "action",
            "parameters",
            "result_count",
            "target_id",
            "occurred_at",
            "sha256",
            "prev_hash",
        ]
        read_only_fields = fields
