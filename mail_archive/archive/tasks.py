from __future__ import annotations

import io
import tarfile
from celery import shared_task
from django.utils import timezone
from core.storage import S3Storage
from core.hash_utils import sha256_bytes
from .models import ArchivedEmail, ExportJob


@shared_task(bind=True, max_retries=3)
def build_export_archive(self, job_id: int):
    storage = S3Storage()
    job = ExportJob.objects.get(id=job_id)
    queryset = ArchivedEmail.objects.filter(
        mailbox=job.mailbox,
        received_at__range=(job.time_start, job.time_end),
    ).order_by("received_at")
    buffer = io.BytesIO()
    with tarfile.open(mode="w:gz", fileobj=buffer) as tar:
        for email in queryset.iterator():
            obj = storage.client.get_object(Bucket=storage.bucket, Key=email.s3_object_key)
            body = obj["Body"].read()
            info = tarfile.TarInfo(name=f"{email.id}.eml")
            info.size = len(body)
            tar.addfile(info, io.BytesIO(body))
    buffer.seek(0)
    export_key = f"exports/{job.id}.tar.gz"
    storage.client.put_object(
        Bucket=storage.bucket,
        Key=export_key,
        Body=buffer.getvalue(),
        ServerSideEncryption="AES256",
    )
    job.mark_complete(export_key)
    return {"sha256": sha256_bytes(buffer.getvalue()), "count": queryset.count()}
