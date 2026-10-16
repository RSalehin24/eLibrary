from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from django.utils import timezone
from django_otp.oath import TOTP


class SecurityClock:
    timestamp = datetime(2026, 10, 14, tzinfo=UTC).timestamp()

    def now(self):
        return datetime.fromtimestamp(self.timestamp, UTC)

    def token(self, device):
        authenticator = TOTP(
            device.bin_key, device.step, device.t0, device.digits, device.drift
        )
        authenticator.time = self.timestamp
        return str(authenticator.token()).zfill(device.digits)

    def incorrect_token(self, device):
        authenticator = TOTP(
            device.bin_key, device.step, device.t0, device.digits, device.drift
        )
        accepted = set()
        for offset in range(-device.tolerance, device.tolerance + 1):
            authenticator.time = self.timestamp + offset * device.step
            accepted.add(str(authenticator.token()).zfill(device.digits))
        return next(
            str(value).zfill(device.digits)
            for value in range(len(accepted) + 1)
            if str(value).zfill(device.digits) not in accepted
        )


@pytest.fixture
def security_clock(monkeypatch):
    clock = SecurityClock()
    monkeypatch.setattr(
        "django_otp.plugins.otp_totp.models.time",
        SimpleNamespace(time=lambda: clock.timestamp),
    )
    monkeypatch.setattr(timezone, "now", clock.now)
    return clock
