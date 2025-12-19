import hashlib
import json
from datetime import date, datetime
from django.db import transaction
from django.utils import timezone
from .models import AuditLog


def _sanitize(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize(v) for v in value]
    return value


class AuditService:
    @staticmethod
    @transaction.atomic
    def append(actor, action: str, parameters: dict, *, result_count=None, target_id=None):
        clean_params = _sanitize(parameters)
        payload = {
            "actor": actor.id,
            "action": action,
            "parameters": clean_params,
            "result_count": result_count,
            "target_id": target_id,
            "ts": timezone.now().isoformat(),
        }
        serialized = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        prev = AuditLog.objects.select_for_update().order_by("-id").first()
        prev_hash = prev.sha256 if prev else None
        sha = hashlib.sha256()
        sha.update(serialized.encode())
        if prev_hash:
            sha.update(prev_hash.encode())
        entry = AuditLog.objects.create(
            actor=actor,
            actor_role=",".join(actor.role_codes),
            action=action,
            parameters=clean_params,
            result_count=result_count,
            target_id=target_id,
            prev_hash=prev_hash,
            sha256=sha.hexdigest(),
        )
        return entry
