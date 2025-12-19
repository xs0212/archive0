from __future__ import annotations

import datetime as dt
import boto3
from django.conf import settings


class S3Storage:
    def __init__(self):
        cfg = settings.S3_STORAGE
        self.bucket = cfg["BUCKET"]
        self.client = boto3.client(
            "s3",
            endpoint_url=cfg["ENDPOINT"],
            aws_access_key_id=cfg["ACCESS_KEY"],
            aws_secret_access_key=cfg["SECRET_KEY"],
            region_name=cfg["REGION"],
        )

    def put_object(self, key: str, data: bytes, retain_days: int | None = None) -> str:
        retain_until = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=retain_days or settings.S3_STORAGE["LOCK_RETENTION_DAYS"])
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ObjectLockMode="COMPLIANCE",
            ObjectLockRetainUntilDate=retain_until,
            ServerSideEncryption="AES256",
        )
        return key

    def presign(self, key: str, expires: int = 300) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires,
        )
