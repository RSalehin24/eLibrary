from stat import S_IMODE

import pytest

from deploy.prepare_environment import (
    canonical_hostname,
    environment_values,
    write_environment,
)


@pytest.mark.parametrize(
    "hostname",
    [
        "https://example.test",
        "example.test:443",
        "../example.test",
        "bad..example",
        "-bad.example",
        "example",
        "example.test\ninjected",
    ],
)
def test_environment_rejects_non_host_values(hostname):
    with pytest.raises(ValueError):
        canonical_hostname(hostname)


def test_environment_normalizes_idna_and_generates_separate_credentials(tmp_path):
    values = environment_values("LIBRARY.Example.Test", tmp_path)
    assert values["PUBLIC_HOST"] == "library.example.test"
    assert values["PUBLIC_SITE_URL"] == "https://library.example.test"
    assert (
        len(
            {
                values[name]
                for name in (
                    "APP_DATABASE_PASSWORD",
                    "POSTGRES_ADMIN_PASSWORD",
                    "REDIS_PASSWORD",
                    "RABBITMQ_PASSWORD",
                    "DJANGO_SECRET_KEY",
                )
            }
        )
        == 5
    )
    assert values["APP_DATABASE_PASSWORD"] in values["DATABASE_URL"]
    assert values["REDIS_PASSWORD"] in values["REDIS_CACHE_URL"]
    assert values["RABBITMQ_PASSWORD"] in values["CELERY_BROKER_URL"]


def test_private_environment_is_exclusive_and_preserves_existing_files(tmp_path):
    output = tmp_path / "platform.env"
    write_environment(output, {"PUBLIC_HOST": "library.example.test"})
    assert S_IMODE(output.stat().st_mode) == 0o600
    original = output.read_bytes()
    with pytest.raises(FileExistsError):
        write_environment(output, {"PUBLIC_HOST": "other.example.test"})
    assert output.read_bytes() == original


def test_newlines_cannot_inject_environment_fields(tmp_path):
    output = tmp_path / "invalid.env"
    with pytest.raises(ValueError):
        write_environment(output, {"TLS_DIRECTORY": "directory\nINJECTED=value"})
    assert not output.exists()
