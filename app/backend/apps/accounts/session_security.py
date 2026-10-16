from django.contrib.auth import update_session_auth_hash

SECURITY_POLICY_FIELDS = frozenset({"is_active", "totp_required"})


def prepare_security_save(user, options):
    fields = options.get("update_fields")
    selected = (
        SECURITY_POLICY_FIELDS
        if fields is None
        else SECURITY_POLICY_FIELDS.intersection(fields)
    )
    if not selected or user._state.adding:
        return
    previous = (
        type(user)
        .objects.select_for_update(no_key=True)
        .filter(pk=user.pk)
        .values("session_revision", *selected)
        .get()
    )
    if not any(getattr(user, field) != previous[field] for field in selected):
        user.session_revision = max(user.session_revision, previous["session_revision"])
        return
    user.session_revision = previous["session_revision"] + 1
    if fields is not None:
        options["update_fields"] = {*fields, "session_revision"}


def rotate_account_sessions(user):
    user.session_revision += 1
    user.save(update_fields=["session_revision", "updated_at"])


def preserve_current_session(request):
    request.user.refresh_from_db(fields=["session_revision"])
    update_session_auth_hash(request, request.user)
