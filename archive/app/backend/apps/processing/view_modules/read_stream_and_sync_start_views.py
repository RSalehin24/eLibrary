import json
import time

from django.http import StreamingHttpResponse
from rest_framework.exceptions import ValidationError
from rest_framework.renderers import BaseRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import CanManageProcessing

from .models import (
    BookCreationRequest,
    BookRecord,
    ProcessingAutomationKind,
    ProcessingSyncStatus,
)
from .serializers import (
    AutomationUpdateSerializer,
    BookCreationRequestSerializer,
    BookRecordSerializer,
    BulkIdsSerializer,
    RequestActionSerializer,
    SyncStartSerializer,
)
from .services import (
    PROCESSING_CARD_KEYS,
    PROCESSING_PAGE_DOMAINS,
    PROCESSING_SYNC_KEY_CATALOG,
    PROCESSING_SYNC_KEY_INCOMPLETE,
    active_sync_scope,
    allow_processing_remote_page_payloads,
    apply_request_action,
    collect_processing_ui_version_updates,
    create_requests_for_record_ids,
    get_sync_state,
    pause_sync,
    processing_card_payload,
    processing_state_payload,
    processing_table_payload,
    processing_ui_versions_diff,
    processing_ui_versions_map,
    resume_sync,
    run_catalog_automation,
    run_incomplete_automation,
    run_manual_catalog_sync,
    sync_run_mode,
    stop_sync,
    update_automation_settings,
)


def truthy_query_param(raw_value, *, default):
    if raw_value is None:
        return default

    normalized = str(raw_value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def int_query_param(raw_value, *, default, minimum=0, maximum=None):
    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        parsed = default

    parsed = max(minimum, parsed)
    if maximum is not None:
        parsed = min(maximum, parsed)
    return parsed


def normalize_sync_scope(raw_scope, *, default=PROCESSING_SYNC_KEY_CATALOG):
    scope = str(raw_scope or default).strip().lower()
    if scope in {PROCESSING_SYNC_KEY_CATALOG, PROCESSING_SYNC_KEY_INCOMPLETE}:
        return scope
    raise ValidationError({"scope": [f"Unsupported processing scope: {scope}"]})


def requested_resume_run_mode(request, *, default):
    raw_value = request.data.get("runMode") if isinstance(request.data, dict) else None
    if raw_value in {None, ""}:
        return default
    run_mode = str(raw_value).strip()
    valid_modes = {"manual", "catalog_automation", "incomplete_automation"}
    if run_mode not in valid_modes:
        raise ValidationError({"runMode": [f"Unsupported sync run mode: {run_mode}"]})
    return run_mode


def processing_response(payload):
    response = Response(payload)
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response["Pragma"] = "no-cache"
    return response


def normalize_stream_page(raw_page):
    page = str(raw_page or PROCESSING_SYNC_KEY_CATALOG).strip().lower()
    if page in PROCESSING_PAGE_DOMAINS:
        return page
    raise ValidationError({"page": [f"Unsupported processing page: {page}"]})


def processing_mutation_payload(versions, *, extra=None):
    payload = {
        "ok": True,
        "versions": {
            domain: int(version)
            for domain, version in (versions or {}).items()
            if domain in PROCESSING_CARD_KEYS
        },
    }
    if extra:
        payload.update(extra)
    return payload


class EventStreamRenderer(BaseRenderer):
    media_type = "text/event-stream"
    format = "event-stream"
    charset = "utf-8"
    render_style = "binary"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data if data is not None else b""


class ProcessingStateView(APIView):
    permission_classes = [CanManageProcessing]

    def get(self, request):
        include_lists = truthy_query_param(
            request.query_params.get("includeLists"),
            default=True,
        )
        return processing_response(
            processing_state_payload(include_lists=include_lists)
        )


class ProcessingCardView(APIView):
    permission_classes = [CanManageProcessing]

    def get(self, request):
        card = str(request.query_params.get("card") or "").strip()
        if not card:
            raise ValidationError({"card": ["This query parameter is required."]})

        try:
            payload = processing_card_payload(card)
        except KeyError as exc:
            raise ValidationError({"card": [f"Unsupported processing card: {exc.args[0]}"]}) from exc

        return processing_response(payload)


class ProcessingStreamView(APIView):
    permission_classes = [CanManageProcessing]
    renderer_classes = [EventStreamRenderer]

    def get(self, request):
        page = normalize_stream_page(request.query_params.get("page"))
        keepalive_seconds = 15
        poll_interval_seconds = 1
        page_domains = sorted(PROCESSING_PAGE_DOMAINS[page])

        def stream():
            yield "event: connected\ndata: {}\n\n"
            last_versions = processing_ui_versions_map(domains=page_domains)
            idle_seconds = 0
            try:
                while True:
                    time.sleep(poll_interval_seconds)
                    changed_versions, last_versions = processing_ui_versions_diff(
                        last_versions,
                        domains=page_domains,
                    )
                    if changed_versions:
                        payload = json.dumps(
                            {
                                "eventId": int(time.time() * 1000),
                                "versions": changed_versions,
                            }
                        )
                        yield f"event: versions\ndata: {payload}\n\n"
                        idle_seconds = 0
                    else:
                        idle_seconds += poll_interval_seconds
                        if idle_seconds >= keepalive_seconds:
                            yield ": keepalive\n\n"
                            idle_seconds = 0
            except GeneratorExit:
                return

        response = StreamingHttpResponse(stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response["Pragma"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


class ProcessingTableView(APIView):
    permission_classes = [CanManageProcessing]

    def get(self, request):
        card = str(request.query_params.get("card") or "").strip()
        if not card:
            raise ValidationError({"card": ["This query parameter is required."]})

        try:
            payload = processing_table_payload(
                card,
                query=request.query_params.get("q", ""),
                category=request.query_params.get("category", ""),
                status=request.query_params.get("status", ""),
                offset=int_query_param(
                    request.query_params.get("offset"),
                    default=0,
                    minimum=0,
                ),
                limit=int_query_param(
                    request.query_params.get("limit"),
                    default=60,
                    minimum=1,
                    maximum=600,
                ),
                include_facets=truthy_query_param(
                    request.query_params.get("includeFacets"),
                    default=True,
                ),
            )
        except KeyError as exc:
            raise ValidationError({"card": [f"Unsupported processing table: {exc.args[0]}"]}) from exc

        return processing_response(payload)


class ProcessingSyncStartView(APIView):
    permission_classes = [CanManageProcessing]

    def post(self, request):
        serializer = SyncStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        remote_pages = (
            serializer.validated_data.get("remotePages")
            if allow_processing_remote_page_payloads()
            else None
        )
        with collect_processing_ui_version_updates() as versions:
            run_manual_catalog_sync(remote_pages or None)
        return processing_response(
            processing_mutation_payload(
                versions,
            )
        )
