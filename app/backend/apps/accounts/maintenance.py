from django import forms
from django.conf import settings
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.admin.sites import AdminSite
from django.utils.translation import gettext_lazy as _

from apps.accounts.otp_verification import attach_verified_device, verify_login_token


def maintenance_requires_otp(user):
    return user is not None and (user.totp_required or user.has_totp_enabled)


class MaintenanceAuthenticationForm(AdminAuthenticationForm):
    otp_token = forms.RegexField(
        regex=r"^[0-9]{6}([0-9]{2})?$",
        required=False,
        max_length=8,
        label=_("Authenticator code (if enabled)"),
        widget=forms.TextInput(
            attrs={"inputmode": "numeric", "autocomplete": "one-time-code"}
        ),
    )

    def clean(self):
        self.cleaned_data = super().clean()
        user = self.get_user()
        if maintenance_requires_otp(user):
            if user.requires_totp_setup:
                raise forms.ValidationError(
                    "Complete two-factor setup in your library profile before opening maintenance."
                )
            token = self.cleaned_data.get("otp_token", "")
            if not token:
                raise forms.ValidationError(
                    "Enter a fresh authenticator code to open maintenance."
                )
            device = verify_login_token(user, token)
            if not device:
                raise forms.ValidationError(
                    "Enter a fresh authenticator code to open maintenance."
                )
            attach_verified_device(user, device)
        return self.cleaned_data


class MaintenanceAdminSite(AdminSite):
    login_form = MaintenanceAuthenticationForm
    login_template = "admin/maintenance_login.html"

    def login(self, request, extra_context=None):
        context = {
            **(extra_context or {}),
            "library_profile_url": f"{settings.FRONTEND_BASE_URL}/profile/",
        }
        return super().login(request, extra_context=context)

    def has_permission(self, request):
        if not super().has_permission(request):
            return False
        if not maintenance_requires_otp(request.user):
            return True
        return request.user.is_verified() and request.user.otp_device.confirmed
