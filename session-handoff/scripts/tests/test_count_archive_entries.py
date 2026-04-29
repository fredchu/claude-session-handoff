import json
import os
import subprocess
import sys
import tempfile
import pathlib

SCRIPT = pathlib.Path(__file__).parent.parent / "count_archive_entries.py"


def make_entry(date, agent="Pro CC", summary="summary"):
    return (
        f"<div><b>{date} Agent [{agent}] — {summary}</b></div>"
        f"<div>detail</div>"
    )


def run_count(html, env=None):
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False, encoding="utf-8"
    ) as f:
        f.write(html)
        fname = f.name
    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--archive-html", fname],
            capture_output=True,
            text=True,
            env=env,
        )
    finally:
        os.unlink(fname)
    return result


def test_five_entries():
    html = "".join(make_entry(f"2026/04/2{i}") for i in range(5))
    r = run_count(html)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["count"] == 5
    assert data["should_consolidate"] is True


def test_twelve_entries():
    html = "".join(make_entry(f"2026/04/{i + 1:02d}") for i in range(12))
    r = run_count(html)
    data = json.loads(r.stdout)
    assert data["count"] == 12
    assert data["should_consolidate"] is True


def test_zero_entries():
    r = run_count("<div>no entries</div>")
    data = json.loads(r.stdout)
    assert data["count"] == 0
    assert data["should_consolidate"] is False


def test_missing_agent_tag():
    # Header without [Agent] bracket — should not parse as valid entry
    html = "<div><b>2026/04/29 — missing agent</b></div>"
    r = run_count(html)
    data = json.loads(r.stdout)
    assert data["count"] == 0


def test_threshold_env_override():
    import os as _os
    env = _os.environ.copy()
    env["CLAUDE_HANDOFF_ARCHIVE_THRESHOLD"] = "3"
    html = "".join(make_entry(f"2026/04/2{i}") for i in range(3))
    r = run_count(html, env=env)
    data = json.loads(r.stdout)
    assert data["threshold"] == 3
    assert data["should_consolidate"] is True
