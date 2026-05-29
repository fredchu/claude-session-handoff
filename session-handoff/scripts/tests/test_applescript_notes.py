import subprocess
import sys
import pathlib

SCRIPT = pathlib.Path(__file__).parent.parent / "applescript_notes.py"
sys.path.insert(0, str(SCRIPT.parent))
import applescript_notes


def test_top_level_help():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "read" in result.stdout or "write" in result.stdout or "exists" in result.stdout


def test_read_subcommand_help():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "read", "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "--title" in result.stdout


def test_write_subcommand_help():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "write", "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "--title" in result.stdout
    assert "--html" in result.stdout


def test_exists_subcommand_help():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "exists", "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "--title" in result.stdout


def test_dedup_subcommand_help():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "dedup", "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "--title" in result.stdout
    assert "--apply" in result.stdout


def test_note_lookup_scripts_use_exact_title_matching():
    scripts = [
        applescript_notes.build_read_script("Session", "Folder", "iCloud"),
        applescript_notes.build_write_script("Session", "Folder", "iCloud", "<div>ok</div>"),
        applescript_notes.build_exists_script("Session", "Folder", "iCloud"),
    ]

    for script in scripts:
        assert 'whose name is "Session"' in script
        assert "whose name contains" not in script


def test_build_dedup_list_script_uses_exact_title_matching():
    script = applescript_notes.build_dedup_list_script("Session", "Folder", "iCloud")
    assert 'whose name is "Session"' in script
    assert "whose name contains" not in script


def test_build_dedup_list_script_emits_locale_independent_sort_key():
    script = applescript_notes.build_dedup_list_script("Session", "Folder", "iCloud")
    # Must produce a YYYYMMDDHHMMSS key, not rely on the localized date string.
    assert "pad2" in script
    assert "sortKey" in script


def test_sort_dedup_rows_orders_chronologically_not_by_locale_string():
    # Regression: sorting the localized modification-date string put "5月6日"
    # after "5月29日". The fixed-width sort_key must order these correctly.
    rows = [
        {"id": "old-may6", "sort_key": "20260506141049", "modified_at": "2026年5月6日 下午2:10:49"},
        {"id": "newest-may29-10am", "sort_key": "20260529104900", "modified_at": "2026年5月29日 上午10:49:00"},
        {"id": "may29-8am", "sort_key": "20260529084900", "modified_at": "2026年5月29日 上午8:49:00"},
    ]
    ordered = applescript_notes._sort_dedup_rows(rows)
    assert [r["id"] for r in ordered] == ["newest-may29-10am", "may29-8am", "old-may6"]


def test_write_lint_failure_p_tag():
    # Writing HTML with forbidden <p> tag should exit 2
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "write",
         "--title", "TestNote",
         "--html-string", "<p>bad content</p>"],
        capture_output=True, text=True,
    )
    assert result.returncode == 2
    assert "ERROR" in result.stderr


def test_write_lint_failure_font_size():
    # Writing HTML with font-size should exit 2
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "write",
         "--title", "TestNote",
         "--html-string", '<div style="font-size: 14px">bad</div>'],
        capture_output=True, text=True,
    )
    assert result.returncode == 2
    assert "ERROR" in result.stderr


def test_write_mutually_exclusive_html_source():
    # Providing both --html-file and --html-string should fail
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "write",
         "--title", "TestNote",
         "--html-string", "<div>ok</div>",
         "--html-file", "/tmp/nonexistent.html"],
        capture_output=True, text=True,
    )
    # argparse exits 2 on argument error
    assert result.returncode == 2
