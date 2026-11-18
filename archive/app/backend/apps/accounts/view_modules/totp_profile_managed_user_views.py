

class TOTPStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        pending_setup = TOTPDevice.objects.filter(user=request.user, confirmed=False).exists()
        return Response(
            TOTPStatusSerializer(
                {
                    "enabled": request.user.has_totp_enabled,
                    "pending_setup": pending_setup,
                    "required": request.user.totp_required,
                    "setup_required": request.user.requires_totp_setup,
                }
            ).data
        )


class TOTPSetupView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        TOTPDevice.objects.filter(user=request.user, confirmed=False).delete()
        device = TOTPDevice.objects.create(user=request.user, name="default", confirmed=False)
        return Response(TOTPSetupSerializer(TOTPSetupSerializer.from_device(device)).data)


class TOTPConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = TOTPConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        device = TOTPDevice.objects.filter(user=request.user, confirmed=False).first()
        if device is None:
            return Response({"detail": "No pending TOTP setup exists."}, status=status.HTTP_400_BAD_REQUEST)

        if not device.verify_token(serializer.validated_data["token"]):
            return Response({"detail": "Invalid TOTP token."}, status=status.HTTP_400_BAD_REQUEST)

        device.confirmed = True
        device.save(update_fields=["confirmed"])
        if request.user.email_setup_pending and request.user.has_usable_password():
            request.user.email_setup_pending = False
            request.user.save(update_fields=["email_setup_pending"])
        return Response({"detail": "TOTP is now enabled."})


class TOTPCancelSetupView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        TOTPDevice.objects.filter(user=request.user, confirmed=False).delete()
        return Response({"detail": "Pending TOTP setup canceled."})


class TOTPDisableView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        if request.user.totp_required:
            return Response(
                {"detail": "An administrator requires TOTP for this account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        deleted, _ = TOTPDevice.objects.filter(user=request.user).delete()
        if not deleted:
            return Response({"detail": "TOTP is not enabled for this account."}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "TOTP has been disabled."})


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get(self, request):
        return Response(ProfileSerializer(request.user, context={"request": request}).data)

    def patch(self, request):
        serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        if getattr(serializer, "password_changed", False):
            update_session_auth_hash(request, request.user)
        return Response(ProfileSerializer(request.user, context={"request": request}).data)


class ManagedUserListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get_queryset(self):
        user_model = get_user_model()
        global_grants = PermissionGrant.objects.active().filter(
            book__isnull=True,
            category__isnull=True,
            contributor__isnull=True,
        )
        return (
            user_model.objects.annotate(
                grant_count_value=Count("permission_grants", distinct=True),
                has_totp_enabled_value=Exists(
                    TOTPDevice.objects.filter(user_id=OuterRef("pk"), confirmed=True)
                ),
            )
            .prefetch_related(
                Prefetch(
                    "permission_grants",
                    queryset=global_grants,
                    to_attr="prefetched_active_global_grants",
                )
            )
        )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ManagedUserCreateSerializer
        return ManagedUserSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        query = request.query_params.get("q", "")
        status_filter = normalized_managed_user_status(
            request.query_params.get("status", "all")
        )
        sort_key = str(request.query_params.get("sort", "name_asc") or "name_asc").strip()
        offset = clamped_query_int(
            request.query_params.get("offset"),
            default=0,
            minimum=0,
        )
        limit = clamped_query_int(
            request.query_params.get("limit"),
            default=MANAGED_USER_DEFAULT_LIMIT,
            minimum=1,
            maximum=MANAGED_USER_MAX_LIMIT,
        )

        if status_filter == "active":
            queryset = queryset.filter(is_active=True)
        elif status_filter == "disabled":
            queryset = queryset.filter(is_active=False)
        elif status_filter == "totp_required":
            queryset = queryset.filter(totp_required=True)

        queryset = apply_managed_user_search(queryset, query)
        queryset = ordered_managed_users_queryset(queryset, sort_key)

        total_count = queryset.count()
        rows = list(queryset[offset : offset + limit])
        next_offset = offset + len(rows)

        return Response(
            {
                "rows": ManagedUserSerializer(
                    rows,
                    many=True,
                    context={"request": request},
                ).data,
                "pagination": {
                    "offset": offset,
                    "limit": limit,
                    "totalCount": total_count,
                    "hasMore": next_offset < total_count,
                    "nextOffset": next_offset,
                },
            }
        )


class ManagedUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get_queryset(self):
        return get_user_model().objects.order_by("email")

    def get_serializer_class(self):
        if self.request.method in {"PUT", "PATCH"}:
            return ManagedUserUpdateSerializer
        return ManagedUserSerializer

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.pk == request.user.pk:
            return Response({"detail": "You cannot edit your own account from Users & Access."}, status=status.HTTP_400_BAD_REQUEST)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_superuser:
            return Response({"detail": "Super admin users cannot be deleted."}, status=status.HTTP_400_BAD_REQUEST)
        if instance.pk == request.user.pk:
            return Response({"detail": "You cannot delete your own account."}, status=status.HTTP_400_BAD_REQUEST)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ManagedUserResendSetupEmailView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    @transaction.atomic
    def post(self, request, pk):
        user = get_user_model().objects.filter(pk=pk).first()
        if user is None:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        if user.is_superuser:
            return Response({"detail": "Super admin users do not use setup emails."}, status=status.HTTP_400_BAD_REQUEST)
        if user.pk == request.user.pk:
            return Response({"detail": "You cannot send a setup email to your own account."}, status=status.HTTP_400_BAD_REQUEST)
        if not user.can_resend_setup_email:
            return Response({"detail": "This user does not need a setup email."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            send_account_setup_email(user, request=request, invited_by=request.user)
        except Exception:
            return Response({"detail": "Setup email could not be delivered."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ManagedUserSerializer(user, context={"request": request}).data)
