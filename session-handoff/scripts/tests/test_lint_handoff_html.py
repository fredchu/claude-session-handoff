import datetime as dt
import pathlib
import subprocess
import sys

from markdown_storage import render_markdown

SCRIPT = pathlib.Path(__file__).parent.parent / "lint_handoff_html.py"


def document(body="hello", **overrides):
    metadata = {
        "schema_version": 1,
        "kind": "shared",
        "agent": "Mini CC",
        "updated_at": "2026-07-17T10:00:00+08:00",
    }
    metadata.update(overrides)
    return render_markdown(metadata, body)


def run_lint(markdown, extra_args=None):
    args = [sys.executable, str(SCRIPT), f"--markdown-string={markdown}"]
    return subprocess.run(args + (extra_args or []), capture_output=True, text=True)


def test_valid_markdown():
    result = run_lint(document(), ["--kind", "shared"])
    assert result.returncode == 0
    assert "OK: 5 chars" in result.stdout


def test_empty_frontmatter_fails():
    result = run_lint("---\n---\ncontent")
    assert result.returncode == 1
    assert "empty frontmatter" in result.stdout


def test_corrupt_frontmatter_fails():
    result = run_lint("---\nschema_version: nope\n---\ncontent")
    assert result.returncode == 1
    assert "schema_version must be an integer" in result.stdout


def test_exceeds_max_chars():
    result = run_lint(document("A" * 20), ["--max-chars", "10"])
    assert result.returncode == 1
    assert "exceeds limit" in result.stdout


def test_stale_timestamp_is_marked():
    from lint_handoff_html import lint_markdown

    now = dt.datetime(2026, 7, 17, 20, 0, tzinfo=dt.timezone(dt.timedelta(hours=8)))
    errors, warnings, _ = lint_markdown(document(), stale_after_hours=4, now=now)
    assert errors == []
    assert warnings == ["WARNING: stale handoff from 2026-07-17T10:00:00+08:00 (10.0h old)"]
