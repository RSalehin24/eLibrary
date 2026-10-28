from django.contrib import admin

from apps.ingestion.models import (
    BookSubmission,
    MatchCandidate,
    ProcessingJob,
    ProcessingLog,
    SourceCatalogEntry,
    TitleResolutionAttempt,
)

admin.site.register(SourceCatalogEntry)
admin.site.register(BookSubmission)
admin.site.register(TitleResolutionAttempt)
admin.site.register(MatchCandidate)
admin.site.register(ProcessingJob)
admin.site.register(ProcessingLog)

# Register your models here.
