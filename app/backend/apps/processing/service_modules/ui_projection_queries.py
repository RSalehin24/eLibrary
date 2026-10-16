from ..models import (
    ProcessingAutomationKind,
    ProcessingUiDomainVersion,
    ProcessingUiProjection,
)
from . import processing_card_payloads as _cards
from . import service_imports_and_constants as _constants
from . import state_serializers as _state


def default_processing_summary_payload():
    return {
        "catalog": {
            "records": 0,
            "notCreated": 0,
            "active": 0,
            "created": 0,
            "onHold": 0,
        },
        "create": {
            "requests": 0,
            "queue": 0,
            "processing": 0,
            "created": 0,
        },
        "onHold": {
            "paused": 0,
            "failed": 0,
            "duplicate": 0,
            "deleted": 0,
        },
        "incomplete": {
            "incomplete": 0,
            "resolved": 0,
        },
        "notifications": {
            "activeRequests": 0,
            "createdCount": 0,
            "failedCount": 0,
            "duplicateCount": 0,
            "latestFailedMessage": "",
        },
    }


def default_processing_shared_projection_payload(key):
    summary = default_processing_summary_payload()
    shared_payloads = {
        _constants.PROCESSING_CARD_CATALOG_OVERVIEW: {
            "card": _constants.PROCESSING_CARD_CATALOG_OVERVIEW,
            "summary": summary["catalog"],
            "notifications": summary["notifications"],
        },
        _constants.PROCESSING_CARD_CATALOG_SYNC: {
            "card": _constants.PROCESSING_CARD_CATALOG_SYNC,
            "sync": _state.default_sync_state_payload(
                _constants.PROCESSING_SYNC_KEY_CATALOG
            ),
        },
        _constants.PROCESSING_CARD_CATALOG_AUTOMATION: {
            "card": _constants.PROCESSING_CARD_CATALOG_AUTOMATION,
            "sync": _state.default_sync_state_payload(
                _constants.PROCESSING_SYNC_KEY_CATALOG
            ),
            "automation": _state.default_automation_payload(
                ProcessingAutomationKind.CATALOG
            ),
        },
        _constants.PROCESSING_CARD_CREATE_OVERVIEW: {
            "card": _constants.PROCESSING_CARD_CREATE_OVERVIEW,
            "summary": summary["create"],
        },
        _constants.PROCESSING_CARD_ON_HOLD_OVERVIEW: {
            "card": _constants.PROCESSING_CARD_ON_HOLD_OVERVIEW,
            "summary": summary["onHold"],
        },
        _constants.PROCESSING_CARD_INCOMPLETE_OVERVIEW: {
            "card": _constants.PROCESSING_CARD_INCOMPLETE_OVERVIEW,
            "summary": summary["incomplete"],
        },
        _constants.PROCESSING_CARD_INCOMPLETE_AUTOMATION: {
            "card": _constants.PROCESSING_CARD_INCOMPLETE_AUTOMATION,
            "sync": _state.default_sync_state_payload(
                _constants.PROCESSING_SYNC_KEY_INCOMPLETE
            ),
            "automation": _state.default_automation_payload(
                ProcessingAutomationKind.INCOMPLETE
            ),
        },
    }
    return shared_payloads.get(key, {})


def processing_sync_payload_has_activity(payload, *, scope):
    if not isinstance(payload, dict):
        return False

    default_payload = _state.default_sync_state_payload(scope)
    if payload.get("status") != default_payload["status"]:
        return True
    if payload.get("message") != default_payload["message"]:
        return True
    if payload.get("runMode") != default_payload["runMode"]:
        return True
    if payload.get("triggerSource") != default_payload["triggerSource"]:
        return True
    if payload.get("progress") is not None:
        return True
    for field_name in (
        "fetchedCount",
        "skippedCount",
        "updatedCount",
        "appendedCount",
        "pageIndex",
    ):
        if int(payload.get(field_name) or 0):
            return True
    return bool(payload.get("workerManaged"))


def processing_shared_projection_payloads(*, keys=None):
    requested_keys = [
        key
        for key in (keys or _constants.PROCESSING_SHARED_CARD_KEYS)
        if key in _constants.PROCESSING_SHARED_CARD_KEYS
    ]
    if not requested_keys:
        return {}

    requested_key_set = set(requested_keys)
    payloads = {}

    if requested_key_set & {
        _constants.PROCESSING_CARD_CATALOG_OVERVIEW,
        _constants.PROCESSING_CARD_CREATE_OVERVIEW,
        _constants.PROCESSING_CARD_ON_HOLD_OVERVIEW,
        _constants.PROCESSING_CARD_INCOMPLETE_OVERVIEW,
    }:
        summary = _cards.processing_summary_payload()
        if _constants.PROCESSING_CARD_CATALOG_OVERVIEW in requested_key_set:
            payloads[_constants.PROCESSING_CARD_CATALOG_OVERVIEW] = {
                "card": _constants.PROCESSING_CARD_CATALOG_OVERVIEW,
                "summary": summary["catalog"],
                "notifications": summary["notifications"],
            }
        if _constants.PROCESSING_CARD_CREATE_OVERVIEW in requested_key_set:
            payloads[_constants.PROCESSING_CARD_CREATE_OVERVIEW] = {
                "card": _constants.PROCESSING_CARD_CREATE_OVERVIEW,
                "summary": summary["create"],
            }
        if _constants.PROCESSING_CARD_ON_HOLD_OVERVIEW in requested_key_set:
            payloads[_constants.PROCESSING_CARD_ON_HOLD_OVERVIEW] = {
                "card": _constants.PROCESSING_CARD_ON_HOLD_OVERVIEW,
                "summary": summary["onHold"],
            }
        if _constants.PROCESSING_CARD_INCOMPLETE_OVERVIEW in requested_key_set:
            payloads[_constants.PROCESSING_CARD_INCOMPLETE_OVERVIEW] = {
                "card": _constants.PROCESSING_CARD_INCOMPLETE_OVERVIEW,
                "summary": summary["incomplete"],
            }

    if requested_key_set & {
        _constants.PROCESSING_CARD_CATALOG_SYNC,
        _constants.PROCESSING_CARD_CATALOG_AUTOMATION,
    }:
        catalog_sync = _state.get_sync_state(_constants.PROCESSING_SYNC_KEY_CATALOG)
        catalog_sync_payload = (
            _state.serialize_sync_state(catalog_sync, include_remote_pages=False)
            if catalog_sync.pk
            else _state.default_sync_state_payload(
                _constants.PROCESSING_SYNC_KEY_CATALOG
            )
        )
        if _constants.PROCESSING_CARD_CATALOG_SYNC in requested_key_set:
            payloads[_constants.PROCESSING_CARD_CATALOG_SYNC] = {
                "card": _constants.PROCESSING_CARD_CATALOG_SYNC,
                "sync": catalog_sync_payload,
            }
        if _constants.PROCESSING_CARD_CATALOG_AUTOMATION in requested_key_set:
            catalog_automation = _state.get_automation_settings(
                ProcessingAutomationKind.CATALOG
            )
            catalog_automation_payload = (
                _state.serialize_automation_settings(catalog_automation)
                if catalog_automation.pk
                else _state.default_automation_payload(ProcessingAutomationKind.CATALOG)
            )
            payloads[_constants.PROCESSING_CARD_CATALOG_AUTOMATION] = {
                "card": _constants.PROCESSING_CARD_CATALOG_AUTOMATION,
                "sync": catalog_sync_payload,
                "automation": catalog_automation_payload,
            }

    if _constants.PROCESSING_CARD_INCOMPLETE_AUTOMATION in requested_key_set:
        incomplete_sync = _state.get_sync_state(
            _constants.PROCESSING_SYNC_KEY_INCOMPLETE
        )
        incomplete_automation = _state.get_automation_settings(
            ProcessingAutomationKind.INCOMPLETE
        )
        incomplete_sync_payload = (
            _state.serialize_sync_state(incomplete_sync, include_remote_pages=False)
            if incomplete_sync.pk
            else _state.default_sync_state_payload(
                _constants.PROCESSING_SYNC_KEY_INCOMPLETE
            )
        )
        incomplete_automation_payload = (
            _state.serialize_automation_settings(incomplete_automation)
            if incomplete_automation.pk
            else _state.default_automation_payload(ProcessingAutomationKind.INCOMPLETE)
        )
        payloads[_constants.PROCESSING_CARD_INCOMPLETE_AUTOMATION] = {
            "card": _constants.PROCESSING_CARD_INCOMPLETE_AUTOMATION,
            "sync": incomplete_sync_payload,
            "automation": incomplete_automation_payload,
        }

    return payloads


def ensure_processing_ui_rows():
    ProcessingUiDomainVersion.objects.bulk_create(
        [
            ProcessingUiDomainVersion(domain=domain, version=0)
            for domain in _constants.PROCESSING_CARD_KEYS
        ],
        ignore_conflicts=True,
    )
    shared_payloads = processing_shared_projection_payloads(
        keys=_constants.PROCESSING_SHARED_CARD_KEYS
    )
    ProcessingUiProjection.objects.bulk_create(
        [
            ProcessingUiProjection(key=key, payload=shared_payloads[key])
            for key in _constants.PROCESSING_SHARED_CARD_KEYS
        ],
        ignore_conflicts=True,
    )


def rebuild_processing_ui_state(*, keys=None):
    ensure_processing_ui_rows()
    target_keys = keys or _constants.PROCESSING_SHARED_CARD_KEYS
    shared_payloads = processing_shared_projection_payloads(keys=target_keys)
    for key in target_keys:
        if key not in _constants.PROCESSING_SHARED_CARD_KEYS:
            continue
        ProcessingUiProjection.objects.update_or_create(
            key=key,
            defaults={"payload": shared_payloads[key]},
        )


def processing_ui_versions_map(domains=None):
    target_domains = (
        _constants.PROCESSING_CARD_KEYS if domains is None else list(domains)
    )
    versions = {domain: 0 for domain in target_domains}
    for row in ProcessingUiDomainVersion.objects.filter(domain__in=target_domains):
        versions[row.domain] = int(row.version)
    return versions


def processing_ui_versions_diff(previous_versions, *, domains=None):
    current_versions = processing_ui_versions_map(domains=domains)
    changed_versions = {
        domain: version
        for domain, version in current_versions.items()
        if int(version) > int(previous_versions.get(domain, 0))
    }
    return changed_versions, current_versions


def processing_ui_shared_projection_rows(*, keys=None):
    requested_keys = [
        key
        for key in (keys or _constants.PROCESSING_SHARED_CARD_KEYS)
        if key in _constants.PROCESSING_SHARED_CARD_KEYS
    ]
    projection_rows = {
        row.key: row
        for row in ProcessingUiProjection.objects.filter(key__in=requested_keys)
    }
    return {key: projection_rows.get(key) for key in requested_keys}


def processing_ui_shared_projection_payload(key):
    projection = processing_ui_shared_projection_rows(keys=[key]).get(key)
    if projection is not None:
        return projection.payload or {}
    return default_processing_shared_projection_payload(key)
