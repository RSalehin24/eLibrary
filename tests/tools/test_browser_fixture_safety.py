import importlib.util
from pathlib import Path

import pytest
from django.conf import settings


@pytest.fixture
def browser_seed(monkeypatch):
    directory = Path(__file__).resolve().parents[1] / "web"
    monkeypatch.syspath_prepend(str(directory))
    specification = importlib.util.spec_from_file_location(
        "browser_fixture_seed_safety", directory / "seed_preview.py"
    )
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "configuration",
    [
        ("development", "bangla_library_preview", 55432),
        ("development", "another_database", 55432),
        ("development", "bangla_library", 5432),
        ("production", "bangla_library", 55432),
    ],
)
def test_fixture_seed_rejects_preview_and_other_databases_before_writing(
    browser_seed, monkeypatch, configuration
):
    environment, database_name, port = configuration
    monkeypatch.setattr(settings, "APP_ENV", environment)
    monkeypatch.setattr(
        settings,
        "DATABASES",
        {"default": {"NAME": database_name, "PORT": port}},
    )
    monkeypatch.setattr(
        browser_seed,
        "create_books",
        lambda *_args: pytest.fail("Fixture write attempted"),
    )
    with pytest.raises(RuntimeError, match="Browser fixtures require"):
        browser_seed.seed_fixture()


@pytest.mark.parametrize("port", [55432, "55432"])
def test_fixture_seed_accepts_only_the_named_foundation_database(
    browser_seed, monkeypatch, port
):
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(
        settings,
        "DATABASES",
        {"default": {"NAME": "bangla_library", "PORT": port}},
    )
    browser_seed.require_foundation_database()
