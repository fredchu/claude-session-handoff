import os
import pathlib
import subprocess
import sys

import pytest

import consolidate_archive
from markdown_storage import StorageError, scan_archive_entries, write_archive_entry

SCRIPT = pathlib.Path(__file__).parent.parent / "consolidate_archive.py"


def add_entries(root, count):
    for index in range(count):
        write_archive_entry(
            root,
            "Pro CC",
            f"session-{index}",
            f"summary-{index}",
            f"detail {index}",
            f"2026-07-{index + 1:02d}T10:00:00+08:00",
        )


def run_consolidate(root, episodic, keep=5, *extra):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--archive-dir", str(root / "Archive"),
         "--episodic-dir", str(episodic), "--keep", str(keep), *extra],
        capture_output=True,
        text=True,
    )


def test_moves_old_entries_as_individual_immutable_files(tmp_path):
    root = tmp_path / "store"
    episodic = tmp_path / "episodic"
    add_entries(root, 7)
    result = run_consolidate(root, episodic)
    assert result.returncode == 0
    assert "moved 2" in result.stdout
    assert len(scan_archive_entries(root)) == 5
    moved = list(episodic.glob("*/*.md"))
    assert len(moved) == 2
    assert not list(episodic.glob("*-weekly-report.md"))


def test_dry_run_changes_nothing(tmp_path):
    root = tmp_path / "store"
    episodic = tmp_path / "episodic"
    add_entries(root, 6)
    before = [entry["path"] for entry in scan_archive_entries(root)]
    result = run_consolidate(root, episodic, 5, "--dry-run")
    assert result.returncode == 0
    assert "Would move 1" in result.stdout
    assert [entry["path"] for entry in scan_archive_entries(root)] == before
    assert not episodic.exists()


def test_within_keep_is_noop(tmp_path):
    root = tmp_path / "store"
    episodic = tmp_path / "episodic"
    add_entries(root, 2)
    result = run_consolidate(root, episodic)
    assert result.returncode == 0
    assert "Archive untouched" in result.stdout
    assert len(scan_archive_entries(root)) == 2
    assert not episodic.exists()


def test_empty_archive_is_noop(tmp_path):
    root = tmp_path / "store"
    episodic = tmp_path / "episodic"
    result = run_consolidate(root, episodic)
    assert result.returncode == 0
    assert "nothing to consolidate (0 entries" in result.stdout
    assert not episodic.exists()


def test_corrupt_frontmatter_fails_before_any_move(tmp_path):
    root = tmp_path / "store"
    episodic = tmp_path / "episodic"
    add_entries(root, 6)
    broken = root / "Archive" / "2026" / "broken.md"
    broken.write_text("---\n---\ncontent", encoding="utf-8")
    sources = set((root / "Archive").rglob("*.md"))
    result = run_consolidate(root, episodic)
    assert result.returncode == 1
    assert "empty frontmatter" in result.stderr
    assert set((root / "Archive").rglob("*.md")) == sources
    assert not episodic.exists()


def test_icloud_placeholder_fails_before_any_move(tmp_path):
    root = tmp_path / "store"
    episodic = tmp_path / "episodic"
    add_entries(root, 6)
    placeholder = root / "Archive" / "2026" / ".pending.md.icloud"
    placeholder.write_text("", encoding="utf-8")
    result = run_consolidate(root, episodic)
    assert result.returncode == 1
    assert "iCloud placeholder" in result.stderr
    assert len(list((root / "Archive").rglob("*.md"))) == 6
    assert not episodic.exists()


def test_read_failure_fails_before_destination_write(tmp_path, monkeypatch, capsys):
    episodic = tmp_path / "episodic"

    def fail_read(_):
        raise StorageError("simulated read failure")

    monkeypatch.setattr(
        sys,
        "argv",
        [str(SCRIPT), "--archive-dir", str(tmp_path / "Archive"),
         "--episodic-dir", str(episodic)],
    )
    monkeypatch.setattr(consolidate_archive, "scan_archive_entries", fail_read)
    with pytest.raises(SystemExit) as exc:
        consolidate_archive.main()
    assert exc.value.code == 1
    assert "simulated read failure" in capsys.readouterr().err
    assert not episodic.exists()


def test_episodic_dir_expands_tilde_under_sandboxed_home(tmp_path):
    root = tmp_path / "store"
    sandboxed_home = tmp_path / "home"
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    add_entries(root, 6)
    env = os.environ.copy()
    if os.name == "nt":
        env["USERPROFILE"] = str(sandboxed_home)
        env["HOMEDRIVE"] = sandboxed_home.drive
        env["HOMEPATH"] = str(sandboxed_home)[len(sandboxed_home.drive):]
    else:
        env["HOME"] = str(sandboxed_home)

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--archive-dir",
            str(root / "Archive"),
            "--episodic-dir",
            "~/episodic-target",
            "--keep",
            "5",
        ],
        capture_output=True,
        text=True,
        cwd=cwd,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert len(list((sandboxed_home / "episodic-target").glob("*/*.md"))) == 1
    assert not (cwd / "~").exists()
