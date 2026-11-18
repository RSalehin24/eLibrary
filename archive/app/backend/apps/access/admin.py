from django.contrib import admin

from apps.access.models import Bookmark, Highlight, PermissionGrant, PreviewAccessSession, ReadingSession

admin.site.register(PermissionGrant)
admin.site.register(PreviewAccessSession)
admin.site.register(ReadingSession)
admin.site.register(Bookmark)
admin.site.register(Highlight)

# Register your models here.
