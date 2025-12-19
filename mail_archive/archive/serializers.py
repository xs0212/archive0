from __future__ import annotations

from django.utils import timezone
from rest_framework import serializers
from accounts.models import Mailbox
from .models import ArchivedEmail


class ParticipantSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=["FROM", "TO", "CC", "BCC"])
    address = serializers.EmailField()


class AttachmentSerializer(serializers.Serializer):
    filename = serializers.CharField()
    mime_type = serializers.CharField()
    content = serializers.CharField(help_text="Base64 encoded content", required=False)
    sha256 = serializers.CharField(required=False)
    size_bytes = serializers.IntegerField(required=False)


class ArchiveRequestSerializer(serializers.Serializer):
    mailbox = serializers.EmailField()
    message_id = serializers.CharField()
    subject = serializers.CharField()
    sent_at = serializers.DateTimeField()
    received_at = serializers.DateTimeField()
    raw_eml = serializers.CharField(help_text="Base64 encoded RFC822 payload")
    body_text = serializers.CharField(required=False, allow_blank=True)
    body_html = serializers.CharField(required=False, allow_blank=True)
    participants = ParticipantSerializer(many=True)
    attachments = AttachmentSerializer(many=True, required=False)
    retain_days = serializers.IntegerField(required=False)

    def validate_mailbox(self, value):
        try:
            mailbox = Mailbox.objects.get(address=value)
        except Mailbox.DoesNotExist as exc:
            raise serializers.ValidationError("mailbox_not_found") from exc
        return mailbox


class ArchivedEmailSerializer(serializers.ModelSerializer):
    mailbox = serializers.CharField(source="mailbox.address")
    department = serializers.CharField(source="department.path")

    class Meta:
        model = ArchivedEmail
        fields = [
            "id",
            "message_id",
            "mailbox",
            "department",
            "subject",
            "sent_at",
            "received_at",
            "sha256",
            "size_bytes",
        ]


class ExportJobRequestSerializer(serializers.Serializer):
    mailbox = serializers.PrimaryKeyRelatedField(queryset=Mailbox.objects.all())
    time_start = serializers.DateTimeField()
    time_end = serializers.DateTimeField()


    def validate(self, data):
        if data["time_end"] < data["time_start"]:
            raise serializers.ValidationError("invalid_time_range")
        return data
