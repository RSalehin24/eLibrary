import importlib.util
import os
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "isolated_browser_runner", ROOT / "tests/web/run_isolated.py"
)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_specifications_cannot_escape_the_browser_directory():
    for name in ["../seed_preview.py", "/tmp/private.spec.mjs", "missing.spec.mjs"]:
        with pytest.raises(ValueError, match="existing browser specification"):
            runner.selected_specifications([name])
    assert (
        runner.selected_specifications(["login.spec.mjs"])[0].name == "login.spec.mjs"
    )


def test_each_specification_gets_distinct_private_fixtures_and_both_processes_share_it(
    monkeypatch, tmp_path
):
    calls = []

    def run(command, **options):
        calls.append(
            (
                command,
                options["env"]["FOUNDATION_FIXTURE_PATH"],
                options["env"]["FOUNDATION_BROWSER_SPECIFICATION"],
            )
        )
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(runner.subprocess, "run", run)
    options = SimpleNamespace(artifacts=tmp_path, project="chromium")
    for name in ["login.spec.mjs", "catalog-filters.spec.mjs"]:
        result = runner.run_specification(runner.SPECIFICATIONS / name, options)
        assert result["passed"]
    assert calls[0][1] == calls[1][1]
    assert calls[2][1] == calls[3][1]
    assert calls[0][1] != calls[2][1]
    assert calls[0][2] == calls[1][2] == "login.spec.mjs"
    assert calls[2][2] == calls[3][2] == "catalog-filters.spec.mjs"
    assert calls[0][0][-1].endswith("seed_preview.py")
    pattern = calls[1][0][5]
    assert re.search(pattern, "/tests/web/e2e/login.spec.mjs")
    assert not re.search(pattern, "/tests/web/e2e/other-login.spec.mjs")
    assert not re.search(pattern, "/tests/web/e2e/loginXspecYmjs")
    for path in tmp_path.rglob("*.log"):
        assert os.stat(path).st_mode & 0o777 == 0o600
