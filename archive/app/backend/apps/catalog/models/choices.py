from django.db import models


class ContributorRole(models.TextChoices):
    AUTHOR = "author", "Author"
    TRANSLATOR = "translator", "Translator"
    COMPILER = "compiler", "Compiler"
    EDITOR = "editor", "Editor"
    ILLUSTRATOR = "illustrator", "Illustrator"
    COVER_ARTIST = "cover_artist", "Cover artist"
    PUBLISHER = "publisher", "Publisher"
    OTHER = "other", "Other"


class GeneratedAssetType(models.TextChoices):
    HTML = "html", "HTML"
    EPUB = "epub", "EPUB"
    COVER = "cover", "Cover"


class GeneratedAssetStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    READY = "ready", "Ready"
    FAILED = "failed", "Failed"


class BookRecordType(models.TextChoices):
    DIGITAL = "digital", "Digital"
    MANUAL = "manual", "Manual"


class ManualBindingType(models.TextChoices):
    HARD_COVER = "hard_cover", "Hard Cover"
    PAPER_BACK = "paper_back", "Paper Back"


class CuratedDocumentStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    VALIDATED = "validated", "Validated"
    REVIEW_REQUIRED = "review_required", "Review required"
    INVALID = "invalid", "Invalid"


class CuratedEntityType(models.TextChoices):
    WORK = "work", "Book/work"
    PERSON = "person", "Person"
    ORGANIZATION = "organization", "Organization"
    SERIES = "series", "Series"
    CATEGORY = "category", "Category"
    ASSET = "asset", "Asset"
    PUBLICATION_EVENT = "publication_event", "Publication event"
    METADATA = "metadata", "Metadata"


class CuratedSectionType(models.TextChoices):
    COVER = "cover", "Cover"
    TITLE_PAGE = "title_page", "Title page"
    BOOK_INFO = "book_info", "Book information"
    DEDICATION = "dedication", "Dedication"
    FRONT_MATTER = "front_matter", "Front matter"
    GENERATED_TOC = "generated_toc", "Generated TOC"
    BODY = "body", "Body"
    BACK_MATTER = "back_matter", "Back matter"
