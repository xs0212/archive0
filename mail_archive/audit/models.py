from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    actor_role = models.CharField(max_length=128)
    action = models.CharField(max_length=64)
    parameters = models.JSONField()
    result_count = models.IntegerField(null=True, blank=True)
    target_id = models.CharField(max_length=255, null=True, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)
    sha256 = models.CharField(max_length=64)
    prev_hash = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        ordering = ["-occurred_at"]
        indexes = [models.Index(fields=["action", "occurred_at"])]
