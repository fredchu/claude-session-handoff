import json
import os
import pathlib
import subprocess
import sys

from markdown_storage import write_archive_entry

SCRIPT = pathlib.Path(__file__).parent.parent / "count_archive_entries.py"


def add_entries(root, count):
    for index in range(count):
        write_archive_entry(
            root,
            "Pro CC",
            f"session-{index}",
            f"summary-{index}",
            "detail",
            f"2026-07-{index + 1:02d}T10:00:00+08:00",
        )


def run_count(root, env=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--archive-dir", str(root / "Archive")],
        capture_output=True,
        text=True,
        env=env,
    )


def test_counts_markdown_entries(tmp_path):
    add_entries(tmp_path, 5)
    result = run_count(tmp_path)
    data = json.loads(result.stdout)
    assert result.returncode == 0
    assert data["count"] == 5
    assert data["should_consolidate"] is True
    assert data["entries"][0]["session_id"] == "session-4"


def test_empty_archive(tmp_path):
    result = run_count(tmp_path)
    assert json.loads(result.stdout)["count"] == 0


def test_threshold_env_override(tmp_path):
    add_entries(tmp_path, 2)
    env = os.environ.copy()
    env["CLAUDE_HANDOFF_ARCHIVE_THRESHOLD"] = "2"
    result = run_count(tmp_path, env)
    assert json.loads(result.stdout)["should_consolidate"] is True


def test_corrupt_entry_fails_closed(tmp_path):
    path = tmp_path / "Archive" / "2026" / "broken.md"
    path.parent.mkdir(parents=True)
    path.write_text("---\n---\ncontent", encoding="utf-8")
    result = run_count(tmp_path)
    assert result.returncode == 1
    assert "empty frontmatter" in result.stderr
