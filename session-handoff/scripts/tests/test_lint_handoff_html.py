import subprocess
import sys
import pathlib

SCRIPT = pathlib.Path(__file__).parent.parent / "lint_handoff_html.py"


def run_lint(html_string, extra_args=None):
    args = [sys.executable, str(SCRIPT), "--html-string", html_string]
    if extra_args:
        args += extra_args
    return subprocess.run(args, capture_output=True, text=True)


def test_valid_html():
    r = run_lint("<div><b>Hello</b></div>")
    assert r.returncode == 0
    assert "OK:" in r.stdout


def test_forbidden_p_tag():
    r = run_lint("<div><p>bad</p></div>")
    assert r.returncode == 1
    assert "ERROR" in r.stdout


def test_forbidden_font_size():
    r = run_lint('<div style="font-size: 14px">bad</div>')
    assert r.returncode == 1
    assert "ERROR" in r.stdout


def test_exceeds_max_chars():
    long_text = "A" * 200
    r = run_lint(f"<div>{long_text}</div>", ["--max-chars", "10"])
    assert r.returncode == 1
    assert "ERROR" in r.stdout


def test_strict_disallowed_tag():
    r = run_lint("<div><table><tr><td>bad</td></tr></table></div>", ["--strict"])
    assert r.returncode == 1
    assert "strict" in r.stdout


def test_strict_valid_html():
    r = run_lint("<div><b>OK</b></div><ul><li>item</li></ul>", ["--strict"])
    assert r.returncode == 0
