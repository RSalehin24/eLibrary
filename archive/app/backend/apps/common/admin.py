from django.contrib import admin

from apps.common.models import AuditLog, SavedFilter

admin.site.register(AuditLog)
admin.site.register(SavedFilter)

# Register your models here.
