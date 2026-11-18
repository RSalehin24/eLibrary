from datetime import time

from django.db import migrations, models
from django.db.models import Q


PROCESSING_DOMAINS = [
    "catalog-overview",
    "catalog-sync",
    "catalog-automation",
    "catalog-records",
    "create-overview",
    "create-requests",
    "create-queue",
    "create-processing",
    "create-created",
    "on-hold-overview",
    "on-hold-paused",
    "on-hold-failed",
    "on-hold-duplicate",
    "on-hold-deleted",
    "incomplete-overview",
    "incomplete-automation",
    "incomplete-records",
    "incomplete-completed",
]

SHARED_PROJECTION_KEYS = [
    "catalog-overview",
    "catalog-sync",
    "catalog-automation",
    "create-overview",
    "on-hold-overview",
    "incomplete-overview",
    "incomplete-automation",
]

INCOMPLETE_KEYWORDS = (
    "incomplete",
    "unfinished",
    "অসম্পূর্ণ",
    "অসম্পূর্ণ বই",
)


def _normalize_automation_settings(settings_model, automation):
    update_fields = []
    if not automation.saved:
        if automation.interval != "weekly":
            automation.interval = "weekly"
            update_fields.append("interval")
        if automation.time != time(3, 0):
            automation.time = time(3, 0)
            update_fields.append("time")
    if automation.status_message == "Not configured.":
        automation.status_message = ""
        update_fields.append("status_message")
    if update_fields:
        automation.save(update_fields=[*update_fields, "updated_at"])
    return automation


def _incomplete_query():
    query = Q()
    for keyword in INCOMPLETE_KEYWORDS:
        query |= Q(category__icontains=keyword)
    return query


def _sync_run_mode(progress):
    progress = progress if isinstance(progress, dict) else {}
    saved_data = progress.get("savedData") if isinstance(progress.get("savedData"), dict) else {}
    return progress.get("runMode") or saved_data.get("runMode") or "manual"


def _sync_phase(progress):
    progress = progress if isinstance(progress, dict) else {}
    return str(progress.get("phase") or "sync")


def _serialize_sync_state(state):
    progress = state.progress if isinstance(state.progress, dict) else None
    return {
        "status": state.status,
        "progress": progress,
        "phase": _sync_phase(progress),
        "fetchedCount": state.fetched_count,
        "skippedCount": state.skipped_count,
        "updatedCount": state.updated_count,
        "appendedCount": state.appended_count,
        "message": state.message,
        "remotePages": [],
        "pageIndex": state.page_index,
        "runMode": _sync_run_mode(progress),
    }


def _serialize_automation_settings(settings):
    return {
        "kind": settings.kind,
        "enabled": settings.enabled,
        "interval": settings.interval,
        "time": settings.time.strftime("%H:%M"),
        "saved": settings.saved,
        "lastRunAt": settings.last_run_at.isoformat() if settings.last_run_at else None,
        "statusMessage": settings.status_message,
    }


def seed_processing_ui_state(apps, schema_editor):
    BookCreationRequest = apps.get_model("processing", "BookCreationRequest")
    BookRecord = apps.get_model("processing", "BookRecord")
    ProcessingAutomationSettings = apps.get_model(
        "processing",
        "ProcessingAutomationSettings",
    )
    ProcessingSyncState = apps.get_model("processing", "ProcessingSyncState")
    ProcessingUiDomainVersion = apps.get_model("processing", "ProcessingUiDomainVersion")
    ProcessingUiProjection = apps.get_model("processing", "ProcessingUiProjection")

    if (
        ProcessingSyncState.objects.filter(singleton_key="default").exists()
        and not ProcessingSyncState.objects.filter(singleton_key="catalog").exists()
    ):
        ProcessingSyncState.objects.filter(singleton_key="default").update(
            singleton_key="catalog"
        )

    for sync_key in ("catalog", "incomplete"):
        ProcessingSyncState.objects.get_or_create(
            singleton_key=sync_key,
            defaults={"message": "Ready to sync."},
        )

    for kind in ("catalog", "incomplete"):
        automation, _ = ProcessingAutomationSettings.objects.get_or_create(
            kind=kind,
            defaults={
                "enabled": False,
                "interval": "weekly",
                "time": time(3, 0),
                "saved": False,
                "status_message": "",
            },
        )
        _normalize_automation_settings(ProcessingAutomationSettings, automation)

    request_counts = {
        state: BookCreationRequest.objects.filter(state=state).count()
        for state in (
            "initial",
            "queued",
            "processing",
            "created",
            "paused",
            "failed",
            "duplicate",
            "deleted",
        )
    }
    active_requests = (
        request_counts["initial"] + request_counts["queued"] + request_counts["processing"]
    )
    on_hold_requests = (
        request_counts["paused"]
        + request_counts["failed"]
        + request_counts["duplicate"]
        + request_counts["deleted"]
    )
    latest_failed_message = (
        BookCreationRequest.objects.filter(state="failed")
        .exclude(error_message="")
        .order_by("-updated_at", "-created_at", "id")
        .values_list("error_message", flat=True)
        .first()
        or ""
    )
    incomplete_records = (
        BookRecord.objects.filter(resolved_from_incomplete=False)
        .filter(Q(was_incomplete=True) | _incomplete_query())
        .count()
    )
    resolved_incomplete = BookRecord.objects.filter(
        was_incomplete=True,
        resolved_from_incomplete=True,
    ).count()
    summary = {
        "catalog": {
            "records": BookRecord.objects.count(),
            "notCreated": BookRecord.objects.filter(book_creation_state="not_created").count(),
            "active": active_requests,
            "created": request_counts["created"],
            "onHold": on_hold_requests,
        },
        "create": {
            "requests": request_counts["initial"],
            "queue": request_counts["queued"],
            "processing": request_counts["processing"],
            "created": request_counts["created"],
        },
        "onHold": {
            "paused": request_counts["paused"],
            "failed": request_counts["failed"],
            "duplicate": request_counts["duplicate"],
            "deleted": request_counts["deleted"],
        },
        "incomplete": {
            "incomplete": incomplete_records,
            "resolved": resolved_incomplete,
        },
        "notifications": {
            "activeRequests": active_requests,
            "createdCount": request_counts["created"],
            "failedCount": request_counts["failed"],
            "duplicateCount": request_counts["duplicate"],
            "latestFailedMessage": latest_failed_message,
        },
    }

    sync_states = {
        state.singleton_key: _serialize_sync_state(state)
        for state in ProcessingSyncState.objects.filter(
            singleton_key__in=("catalog", "incomplete")
        )
    }
    automations = {
        settings.kind: _serialize_automation_settings(settings)
        for settings in ProcessingAutomationSettings.objects.filter(
            kind__in=("catalog", "incomplete")
        )
    }

    projection_payloads = {
        "catalog-overview": {
            "card": "catalog-overview",
            "summary": summary["catalog"],
            "notifications": summary["notifications"],
        },
        "catalog-sync": {
            "card": "catalog-sync",
            "sync": sync_states.get("catalog")
            or {
                "status": "idle",
                "progress": None,
                "phase": "sync",
                "fetchedCount": 0,
                "skippedCount": 0,
                "updatedCount": 0,
                "appendedCount": 0,
                "message": "Ready to sync.",
                "remotePages": [],
                "pageIndex": 0,
                "runMode": "manual",
            },
        },
        "catalog-automation": {
            "card": "catalog-automation",
            "sync": sync_states.get("catalog")
            or {
                "status": "idle",
                "progress": None,
                "phase": "sync",
                "fetchedCount": 0,
                "skippedCount": 0,
                "updatedCount": 0,
                "appendedCount": 0,
                "message": "Ready to sync.",
                "remotePages": [],
                "pageIndex": 0,
                "runMode": "manual",
            },
            "automation": automations.get("catalog")
            or {
                "kind": "catalog",
                "enabled": False,
                "interval": "weekly",
                "time": "03:00",
                "saved": False,
                "lastRunAt": None,
                "statusMessage": "",
            },
        },
        "create-overview": {
            "card": "create-overview",
            "summary": summary["create"],
        },
        "on-hold-overview": {
            "card": "on-hold-overview",
            "summary": summary["onHold"],
        },
        "incomplete-overview": {
            "card": "incomplete-overview",
            "summary": summary["incomplete"],
        },
        "incomplete-automation": {
            "card": "incomplete-automation",
            "sync": sync_states.get("incomplete")
            or {
                "status": "idle",
                "progress": None,
                "phase": "sync",
                "fetchedCount": 0,
                "skippedCount": 0,
                "updatedCount": 0,
                "appendedCount": 0,
                "message": "Ready to sync.",
                "remotePages": [],
                "pageIndex": 0,
                "runMode": "manual",
            },
            "automation": automations.get("incomplete")
            or {
                "kind": "incomplete",
                "enabled": False,
                "interval": "weekly",
                "time": "03:00",
                "saved": False,
                "lastRunAt": None,
                "statusMessage": "",
            },
        },
    }

    for domain in PROCESSING_DOMAINS:
        ProcessingUiDomainVersion.objects.get_or_create(
            domain=domain,
            defaults={"version": 0},
        )

    for key in SHARED_PROJECTION_KEYS:
        ProcessingUiProjection.objects.update_or_create(
            key=key,
            defaults={"payload": projection_payloads[key]},
        )


class Migration(migrations.Migration):
    dependencies = [
        ("processing", "0002_processing_links"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProcessingUiDomainVersion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("domain", models.CharField(max_length=120, unique=True)),
                ("version", models.PositiveBigIntegerField(default=0)),
            ],
            options={"ordering": ["domain"]},
        ),
        migrations.CreateModel(
            name="ProcessingUiProjection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("key", models.CharField(max_length=120, unique=True)),
                ("payload", models.JSONField(blank=True, default=dict)),
            ],
            options={"ordering": ["key"]},
        ),
        migrations.RunPython(seed_processing_ui_state, migrations.RunPython.noop),
    ]
