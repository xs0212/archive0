from __future__ import annotations

import base64
from django.conf import settings
from django.db import transaction
from core.hash_utils import sha256_bytes
from core.storage import S3Storage
from core.search import get_client
from audit.services import AuditService
from .models import ArchivedEmail, EmailAttachment, EmailParticipant


class ArchiveIngestService:
    def __init__(self):
        self.storage = S3Storage()
        self.es = get_client()
        self.index = settings.ELASTICSEARCH["INDEX"]

    @transaction.atomic
    def ingest(self, *, user, payload: dict) -> ArchivedEmail:
        mailbox = payload["mailbox"]
        raw_bytes = base64.b64decode(payload["raw_eml"])
        sha = sha256_bytes(raw_bytes)
        key = f"eml/{payload['received_at'].date()}/{payload['message_id']}.eml"
        self.storage.put_object(key, raw_bytes, retain_days=payload.get("retain_days"))
        email = ArchivedEmail.objects.create(
            message_id=payload["message_id"],
            mailbox=mailbox,
            department=mailbox.department,
            subject=payload["subject"],
            sent_at=payload["sent_at"],
            received_at=payload["received_at"],
            sha256=sha,
            s3_object_key=key,
            size_bytes=len(raw_bytes),
            has_html=bool(payload.get("body_html")),
            has_text=bool(payload.get("body_text")),
        )
        participants = [
            EmailParticipant(email=email, type=p["type"], address=p["address"])
            for p in payload["participants"]
        ]
        EmailParticipant.objects.bulk_create(participants, ignore_conflicts=True)
        attachments = []
        for attachment in payload.get("attachments", []):
            content = attachment.get("content")
            if content:
                content_bytes = base64.b64decode(content)
                att_sha = sha256_bytes(content_bytes)
                att_key = f"attachments/{email.id}/{attachment['filename']}"
                self.storage.put_object(att_key, content_bytes)
                attachments.append(
                    EmailAttachment(
                        email=email,
                        filename=attachment["filename"],
                        mime_type=attachment["mime_type"],
                        size_bytes=len(content_bytes),
                        sha256=att_sha,
                        s3_object_key=att_key,
                    )
                )
            else:
                attachments.append(
                    EmailAttachment(
                        email=email,
                        filename=attachment["filename"],
                        mime_type=attachment["mime_type"],
                        size_bytes=attachment["size_bytes"],
                        sha256=attachment["sha256"],
                        s3_object_key=f"external/{attachment['filename']}",
                    )
                )
        if attachments:
            EmailAttachment.objects.bulk_create(attachments, ignore_conflicts=True)
        self._index(email, payload, sha)
        AuditService.append(user, "ARCHIVE_STORE", {"message_id": email.message_id})
        return email

    def _index(self, email: ArchivedEmail, payload: dict, sha: str):
        doc = {
            "email_id": email.id,
            "message_id": email.message_id,
            "department_path": email.department.path,
            "mailbox": email.mailbox.address,
            "subject": email.subject,
            "body_text": payload.get("body_text", ""),
            "body_html": payload.get("body_html", ""),
            "participants": [p["address"] for p in payload["participants"]],
            "sent_at": payload["sent_at"].isoformat(),
            "received_at": payload["received_at"].isoformat(),
            "sha256": sha,
            "immutable_flag": True,
            "access_tags": [email.department.path, email.mailbox.address],
        }
        self.es.index(index=self.index, id=email.id, document=doc, refresh=False)


class EmailAccessService:
    def __init__(self):
        self.storage = S3Storage()

    def presign(self, email: ArchivedEmail) -> str:
        return self.storage.presign(email.s3_object_key)

    def verify(self, email: ArchivedEmail) -> bool:
        client = self.storage.client
        obj = client.get_object(Bucket=self.storage.bucket, Key=email.s3_object_key)
        contents = obj["Body"].read()
        return email.sha256 == sha256_bytes(contents)
