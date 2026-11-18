

class ProcessingSyncPauseView(APIView):
    permission_classes = [CanManageProcessing]

    def post(self, request, scope=None):
        with collect_processing_ui_version_updates() as versions:
            pause_sync(
                normalize_sync_scope(
                    scope,
                    default=active_sync_scope(),
                )
            )
        return processing_response(
            processing_mutation_payload(
                versions,
            )
        )


class ProcessingSyncResumeView(APIView):
    permission_classes = [CanManageProcessing]

    def post(self, request, scope=None):
        sync_key = normalize_sync_scope(
            scope,
            default=active_sync_scope(),
        )
        default_run_mode = sync_run_mode(get_sync_state(sync_key))
        with collect_processing_ui_version_updates() as versions:
            resume_sync(
                sync_key,
                run_mode=requested_resume_run_mode(
                    request,
                    default=default_run_mode,
                ),
            )
        return processing_response(
            processing_mutation_payload(
                versions,
            )
        )


class ProcessingSyncStopView(APIView):
    permission_classes = [CanManageProcessing]

    def post(self, request, scope=None):
        with collect_processing_ui_version_updates() as versions:
            stop_sync(
                normalize_sync_scope(
                    scope,
                    default=active_sync_scope(),
                )
            )
        return processing_response(
            processing_mutation_payload(
                versions,
            )
        )


class ProcessingRecordCreateRequestsView(APIView):
    permission_classes = [CanManageProcessing]

    def post(self, request):
        serializer = BulkIdsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with collect_processing_ui_version_updates() as versions:
            created = create_requests_for_record_ids(
                serializer.validated_data["ids"],
                actor=request.user,
            )
        return processing_response(
            processing_mutation_payload(
                versions,
                extra={"createdCount": len(created)},
            )
        )


class ProcessingRequestActionView(APIView):
    permission_classes = [CanManageProcessing]

    def post(self, request):
        serializer = RequestActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with collect_processing_ui_version_updates() as versions:
                changed = apply_request_action(
                    serializer.validated_data["ids"],
                    serializer.validated_data["action"],
                    delete_book=serializer.validated_data["deleteBook"],
                    actor=request.user,
                )
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        return processing_response(
            processing_mutation_payload(
                versions,
                extra={"changedCount": len(changed)},
            )
        )


class ProcessingAutomationView(APIView):
    permission_classes = [CanManageProcessing]
    kind = None

    def post(self, request):
        serializer = AutomationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with collect_processing_ui_version_updates() as versions:
            update_automation_settings(self.kind, serializer.validated_data)
        return processing_response(
            processing_mutation_payload(
                versions,
            )
        )


class ProcessingCatalogAutomationView(ProcessingAutomationView):
    kind = ProcessingAutomationKind.CATALOG


class ProcessingIncompleteAutomationView(ProcessingAutomationView):
    kind = ProcessingAutomationKind.INCOMPLETE


class ProcessingCatalogAutomationRunView(APIView):
    permission_classes = [CanManageProcessing]

    def post(self, request):
        with collect_processing_ui_version_updates() as versions:
            run_catalog_automation()
        return processing_response(
            processing_mutation_payload(
                versions,
            )
        )


class ProcessingIncompleteAutomationRunView(APIView):
    permission_classes = [CanManageProcessing]

    def post(self, request):
        with collect_processing_ui_version_updates() as versions:
            run_incomplete_automation()
        return processing_response(
            processing_mutation_payload(
                versions,
            )
        )
