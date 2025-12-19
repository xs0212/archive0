from __future__ import annotations

from django.db import models
from django.utils import timezone
from accounts.models import Department, Mailbox


class ArchivedEmail(models.Model):
    message_id = models.CharField(max_length=255)
    mailbox = models.ForeignKey(Mailbox, on_delete=models.PROTECT)
    department = models.ForeignKey(Department, on_delete=models.PROTECT)
    subject = models.CharField(max_length=512)
    sent_at = models.DateTimeField()
    received_at = models.DateTimeField()
    sha256 = models.CharField(max_length=64)
    s3_object_key = models.CharField(max_length=512)
    size_bytes = models.BigIntegerField()
    has_html = models.BooleanField(default=False)
    has_text = models.BooleanField(default=True)
    immutable_flag = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("message_id", "mailbox")
        indexes = [
            models.Index(fields=["mailbox", "received_at"]),
            models.Index(fields=["department", "received_at"]),
        ]

    def __str__(self):
        return f"{self.mailbox.address}:{self.message_id}"


class EmailParticipant(models.Model):
    email = models.ForeignKey(ArchivedEmail, on_delete=models.CASCADE, related_name="participants")
    type = models.CharField(max_length=4, choices=(
        ("FROM", "FROM"),
        ("TO", "TO"),
        ("CC", "CC"),
        ("BCC", "BCC"),
    ))
    address = models.EmailField()

    class Meta:
        unique_together = ("email", "type", "address")


class EmailAttachment(models.Model):
    email = models.ForeignKey(ArchivedEmail, on_delete=models.CASCADE, related_name="attachments")
    filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=128)
    size_bytes = models.BigIntegerField()
    sha256 = models.CharField(max_length=64)
    s3_object_key = models.CharField(max_length=512)


class SearchQueue(models.Model):
    email = models.ForeignKey(ArchivedEmail, on_delete=models.CASCADE)
    payload = models.JSONField()
    status = models.CharField(max_length=16, default="PENDING")
    retry_count = models.PositiveIntegerField(default=0)
    last_error = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ExportJob(models.Model):
    owner = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    mailbox = models.ForeignKey(Mailbox, on_delete=models.PROTECT)
    time_start = models.DateTimeField()
    time_end = models.DateTimeField()
    status = models.CharField(max_length=16, default="QUEUED")
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    result_s3_key = models.CharField(max_length=512, null=True, blank=True)

    def mark_complete(self, key: str):
        self.status = "COMPLETED"
        self.result_s3_key = key
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "result_s3_key", "completed_at"])
