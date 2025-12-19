from __future__ import annotations

from datetime import datetime
from django.core.exceptions import PermissionDenied
from .models import MailboxAccess, User


class AccessService:
    @staticmethod
    def resolve_tags(user: User, time_range: dict | None = None) -> list[str]:
        tags = {user.department.path}
        for access in user.allowed_mailboxes():
            tags.add(access.mailbox.address)
        if time_range:
            AccessService.ensure_time_scope(user, time_range["time_start"])
            AccessService.ensure_time_scope(user, time_range["time_end"])
        if user.has_permission("GLOBAL_MAILBOX_READ"):
            tags.add("*")
        return list(tags)

    @staticmethod
    def ensure_email_access(user: User, email) -> None:
        if user.has_permission("GLOBAL_MAILBOX_READ"):
            return
        if email.department_id != user.department_id:
            allowed_mailboxes = {a.mailbox_id for a in user.allowed_mailboxes()}
            if email.mailbox_id not in allowed_mailboxes:
                raise PermissionDenied("mailbox_forbidden")

    @staticmethod
    def ensure_time_scope(user: User, sent_at: datetime) -> None:
        if user.has_permission("TIME_UNBOUND"):
            return
        for acc in user.allowed_mailboxes():
            if acc.time_start <= sent_at and (acc.time_end is None or acc.time_end >= sent_at):
                return
        raise PermissionDenied("time_forbidden")

    @staticmethod
    def ensure_mailbox_access(user: User, mailbox) -> None:
        if user.has_permission("GLOBAL_MAILBOX_READ"):
            return
        allowed = {a.mailbox_id for a in user.allowed_mailboxes()}
        if mailbox.id not in allowed:
            raise PermissionDenied("mailbox_forbidden")
