from django.contrib import admin
from .models import ArchivedEmail, EmailAttachment, EmailParticipant, ExportJob

admin.site.register(ArchivedEmail)
admin.site.register(EmailAttachment)
admin.site.register(EmailParticipant)
admin.site.register(ExportJob)
