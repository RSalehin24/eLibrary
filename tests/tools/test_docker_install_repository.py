import subprocess
from pathlib import Path

import pytest

HELPER = (
    Path(__file__).resolve().parents[2] / "deploy/scripts/docker_install_repository.sh"
)


def repository_result(tmp_path, contents):
    release = tmp_path / "os-release"
    release.write_text(contents)
    return subprocess.run(
        [
            "bash",
            "-c",
            'source "$1"; docker_repository_distribution "$2"',
            "test",
            str(HELPER),
            str(release),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(
    "distribution,codename", [("ubuntu", "noble"), ("debian", "bookworm")]
)
def test_supported_distribution_selects_its_own_docker_repository(
    tmp_path, distribution, codename
):
    result = repository_result(
        tmp_path, f"ID={distribution}\nVERSION_CODENAME={codename}\n"
    )
    assert result.returncode == 0
    assert result.stdout.strip() == f"{distribution} {codename}"


@pytest.mark.parametrize(
    "contents",
    [
        "ID=fedora\nVERSION_CODENAME=noble\n",
        "ID=debian\n",
        "VERSION_CODENAME=bookworm\n",
        "ID=ubuntu\nVERSION_CODENAME='noble injected'\n",
    ],
)
def test_unsupported_or_incomplete_distribution_fails_before_installation(
    tmp_path, contents
):
    result = repository_result(tmp_path, contents)
    assert result.returncode != 0
    assert result.stdout == ""
    assert result.stderr
