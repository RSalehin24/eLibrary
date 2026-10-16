import pytest
from config.background_limits import background_limits
from django.core.exceptions import ImproperlyConfigured


def test_runtime_limits_default_to_a_bounded_worker_and_attachment():
    assert background_limits(lambda _name, default: default) == (3600, 20 * 1024 * 1024)


@pytest.mark.parametrize("timeout,attachment", [(60, 1024), (86400, 128 * 1024 * 1024)])
def test_runtime_limits_accept_the_configured_boundaries(timeout, attachment):
    values = {
        "BACKGROUND_JOB_SOFT_TIMEOUT_SECONDS": timeout,
        "KINDLE_MAX_ATTACHMENT_BYTES": attachment,
    }
    assert background_limits(lambda name, default: values.get(name, default)) == (
        timeout,
        attachment,
    )


@pytest.mark.parametrize(
    "option,value",
    [
        ("BACKGROUND_JOB_SOFT_TIMEOUT_SECONDS", 59),
        ("BACKGROUND_JOB_SOFT_TIMEOUT_SECONDS", 86401),
        ("KINDLE_MAX_ATTACHMENT_BYTES", 1023),
        ("KINDLE_MAX_ATTACHMENT_BYTES", 128 * 1024 * 1024 + 1),
    ],
)
def test_runtime_limits_reject_values_outside_the_documented_range(option, value):
    with pytest.raises(ImproperlyConfigured, match=option):
        background_limits(lambda name, default: value if name == option else default)
