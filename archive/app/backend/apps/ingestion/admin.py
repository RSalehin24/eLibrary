from django.contrib import admin

from apps.ingestion.models import (
    BookSubmission,
    DuplicateReview,
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
admin.site.register(DuplicateReview)

# Register your models here.
