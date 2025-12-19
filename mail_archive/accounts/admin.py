from django.contrib import admin
from .models import Department, Role, Permission, User, Mailbox, MailboxAccess, MfaSecret

admin.site.register(Department)
admin.site.register(Role)
admin.site.register(Permission)
admin.site.register(User)
admin.site.register(Mailbox)
admin.site.register(MailboxAccess)
admin.site.register(MfaSecret)
