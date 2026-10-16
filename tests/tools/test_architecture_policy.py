import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def policy():
    path = Path(__file__).resolve().parents[1] / "scripts/check-architecture-policy.py"
    specification = importlib.util.spec_from_file_location("architecture_policy", path)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "expression",
    ["exec(compile(source, path, 'exec'))", "exec ( compile (source, path, 'exec'))"],
)
def test_runtime_source_execution_is_rejected(policy, expression):
    assert policy.uses_runtime_source_loader("app/backend/apps/example.py", expression)


def test_regular_imports_and_retained_test_helpers_remain_supported(policy):
    assert not policy.uses_runtime_source_loader(
        "app/backend/apps/example.py", "from .helpers import run"
    )
    assert not policy.uses_runtime_source_loader(
        "tests/example.py", "exec(compile(source, path, 'exec'))"
    )
