import os
import importlib.util
import subprocess
import sys
import tempfile
import pathlib

SCRIPT = pathlib.Path(__file__).parent.parent / "consolidate_archive.py"

spec = importlib.util.spec_from_file_location("consolidate_archive", SCRIPT)
consolidate_archive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(consolidate_archive)


def make_entry(date, agent="Pro CC", summary="summary"):
    return (
        f"<div><b>{date} Agent [{agent}] — {summary}</b></div>"
        f"<div>detail</div>\n"
    )


def run_consolidate(html, keep=5, extra_args=None):
    with tempfile.TemporaryDirectory() as tmpdir:
        html_file = os.path.join(tmpdir, "archive.html")
        episodic_dir = os.path.join(tmpdir, "episodic")
        os.makedirs(episodic_dir)
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html)
        args = [
            sys.executable, str(SCRIPT),
            "--archive-html", html_file,
            "--episodic-dir", episodic_dir,
            "--keep", str(keep),
        ]
        if extra_args:
            args += extra_args
        result = subprocess.run(args, capture_output=True, text=True)
        files = os.listdir(episodic_dir)
        rebuilt = pathlib.Path(html_file).read_text(encoding="utf-8") if os.path.exists(html_file) else ""
        return result, files, rebuilt


def test_dry_run_plan():
    html = "".join(make_entry(f"2026/04/{i + 10:02d}") for i in range(8))
    result, files, _ = run_consolidate(html, keep=5, extra_args=["--dry-run"])
    assert result.returncode == 0
    assert "Would promote" in result.stdout
    assert len(files) == 0  # dry-run: no files written


def test_cross_week_grouping():
    # April 20 (W17) and April 6 (W15) should produce different week files when promoted
    entries = [
        make_entry("2026/04/06"),  # W15 — will be promoted (old)
        make_entry("2026/04/20"),  # W17 — will be promoted (old)
        make_entry("2026/04/27"),  # W18 — kept
        make_entry("2026/04/28"),  # W18 — kept
        make_entry("2026/04/29"),  # W18 — kept
        make_entry("2026/04/30"),  # W18 — kept
        make_entry("2026/05/01"),  # W18 — kept
    ]
    html = "".join(entries)
    result, files, _ = run_consolidate(html, keep=5)
    assert result.returncode == 0
    promoted_files = [f for f in files if "weekly-report" in f]
    # 7 entries - keep 5 = 2 promoted, across 2 different weeks
    assert len(promoted_files) == 2


def test_keep_correct_count():
    html = "".join(make_entry(f"2026/04/{i + 1:02d}") for i in range(10))
    result, files, _ = run_consolidate(html, keep=3)
    assert result.returncode == 0
    assert "kept 3" in result.stdout


def test_promoted_count_in_summary():
    html = "".join(make_entry(f"2026/04/{i + 1:02d}") for i in range(8))
    result, files, _ = run_consolidate(html, keep=5)
    assert result.returncode == 0
    assert "promoted 3" in result.stdout


def test_rebuild_archive_keeps_n_entries():
    # After consolidation, the archive file should contain only 'keep' entries
    html = "".join(make_entry(f"2026/04/{i + 1:02d}") for i in range(10))
    result, files, rebuilt = run_consolidate(html, keep=3)
    assert result.returncode == 0
    # Count header lines in rebuilt HTML
    import re
    headers = re.findall(r"<div><b>\d{4}/\d{2}/\d{2}", rebuilt)
    assert len(headers) == 3


def test_rebuild_archive_includes_canonical_header():
    html = "".join(make_entry(f"2026/04/{i + 1:02d}") for i in range(3))
    result, files, rebuilt = run_consolidate(html, keep=2)
    assert result.returncode == 0
    assert rebuilt.startswith("<div>Session Handoff — Archive</div>")


def test_apply_requires_episodic_dir(monkeypatch, capsys):
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout=make_entry("2026/04/01"),
            stderr="",
        )

    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--apply"])
    monkeypatch.setattr(consolidate_archive.subprocess, "run", fake_run)

    try:
        consolidate_archive.main()
    except SystemExit as exc:
        assert exc.code != 0
    else:
        raise AssertionError("main() should require --episodic-dir")

    assert "--episodic-dir is required" in capsys.readouterr().err
