from django.contrib import admin

from apps.catalog.models import (
    Book,
    BookCategory,
    BookContributor,
    BookSeries,
    BookSource,
    Category,
    Contributor,
    CuratedBookDocument,
    CuratedEntity,
    CuratedEvidence,
    CuratedSection,
    GeneratedAsset,
    MetadataReview,
    MetadataVersion,
    Series,
    UserBook,
)

@admin.register(Contributor)
class ContributorAdmin(admin.ModelAdmin):
    list_display = ("name", "catalog_code", "slug", "created_at")
    search_fields = ("name", "catalog_code", "slug")


admin.site.register(Series)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "catalog_code", "slug", "created_at")
    search_fields = ("name", "catalog_code", "slug")


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "catalog_code", "record_type", "state", "review_state", "created_at")
    list_filter = ("record_type", "state", "review_state")
    search_fields = ("title", "catalog_code", "slug")


admin.site.register(BookContributor)
admin.site.register(BookSeries)
admin.site.register(BookCategory)
admin.site.register(BookSource)
admin.site.register(CuratedBookDocument)
admin.site.register(CuratedEntity)
admin.site.register(CuratedSection)
admin.site.register(CuratedEvidence)
admin.site.register(GeneratedAsset)
admin.site.register(MetadataReview)
admin.site.register(MetadataVersion)
admin.site.register(UserBook)

# Register your models here.
