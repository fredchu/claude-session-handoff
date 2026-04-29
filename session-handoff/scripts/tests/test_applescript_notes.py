import subprocess
import sys
import pathlib

SCRIPT = pathlib.Path(__file__).parent.parent / "applescript_notes.py"


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
