from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("id", "actor", "action", "occurred_at")
    search_fields = ("action", "actor__username")
    ordering = ("-occurred_at",)
