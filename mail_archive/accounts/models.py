from __future__ import annotations

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone


class Department(models.Model):
    name = models.CharField(max_length=128, unique=True)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT)
    path = models.CharField(max_length=512, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if self.parent:
            self.path = f"{self.parent.path}/{self.name}"
        else:
            self.path = self.name
        super().save(*args, **kwargs)

    def __str__(self):
        return self.path


class Permission(models.Model):
    code = models.CharField(max_length=64, unique=True)
    description = models.CharField(max_length=256)

    def __str__(self):
        return self.code


class Role(models.Model):
    name = models.CharField(max_length=64, unique=True)
    description = models.CharField(max_length=256)
    permissions = models.ManyToManyField(Permission, through="RolePermission", related_name="roles")

    def __str__(self):
        return self.name


class RolePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("role", "permission")


class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not username:
            raise ValueError("Username required")
        if not email:
            raise ValueError("Email required")
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(username, email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=64, unique=True)
    email = models.EmailField(unique=True)
    department = models.ForeignKey(Department, on_delete=models.PROTECT)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    last_login = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    roles = models.ManyToManyField(Role, through="UserRole", related_name="users")

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email", "department"]

    objects = UserManager()

    class Meta:
        ordering = ["username"]

    @property
    def role_codes(self):
        return list(self.roles.values_list("name", flat=True))

    def has_permission(self, code: str) -> bool:
        if self.is_superuser:
            return True
        return self.roles.filter(permissions__code=code).exists()

    def allowed_mailboxes(self):
        now = timezone.now()
        return self.mailbox_access.filter(
            time_start__lte=now,
        ).filter(models.Q(time_end__isnull=True) | models.Q(time_end__gte=now))

    def __str__(self):
        return self.username


class UserRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("user", "role")


class Mailbox(models.Model):
    address = models.EmailField(unique=True)
    department = models.ForeignKey(Department, on_delete=models.PROTECT)
    sensitivity = models.CharField(max_length=32, default="NORMAL")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.address


class MailboxAccess(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="mailbox_access")
    mailbox = models.ForeignKey(Mailbox, on_delete=models.CASCADE, related_name="access_grants")
    time_start = models.DateTimeField()
    time_end = models.DateTimeField(null=True, blank=True)
    scope = models.CharField(max_length=16, choices=(
        ("READ", "READ"),
        ("EXPORT", "EXPORT"),
    ))

    class Meta:
        indexes = [models.Index(fields=["user", "mailbox"])]


class MfaSecret(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="mfa_secret")
    totp_secret = models.BinaryField()
    enrolled_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"MFA:{self.user.username}"
