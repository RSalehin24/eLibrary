import shlex

from automation.lib.env_tools import parse_env_file, render_shell_exports


def test_render_shell_exports_preserves_literal_shell_values(tmp_path):
    source_path = tmp_path / ".env"
    source_path.write_text(
        "# comment\n"
        "DJANGO_SECRET_KEY=abc$g8$r\n"
        "BACKEND_PORT=8000\n"
        "EMPTY_VALUE=\n"
        "ALREADY_QUOTED='leave-me-alone'\n",
        encoding="utf-8",
    )

    rendered = render_shell_exports(parse_env_file(source_path))
    quoted_value = "'leave-me-alone'"

    assert rendered == "\n".join(
        [
            f"export DJANGO_SECRET_KEY={shlex.quote('abc$g8$r')}",
            f"export BACKEND_PORT={shlex.quote('8000')}",
            f"export EMPTY_VALUE={shlex.quote('')}",
            f"export ALREADY_QUOTED={shlex.quote(quoted_value)}",
        ]
    )


def test_render_shell_exports_escapes_single_quotes(tmp_path):
    source_path = tmp_path / ".env"
    source_path.write_text("SECRET=it's-private\n", encoding="utf-8")

    rendered = render_shell_exports(parse_env_file(source_path))

    quoted_value = "it's-private"
    assert rendered == f"export SECRET={shlex.quote(quoted_value)}"
