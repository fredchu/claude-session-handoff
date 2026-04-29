import json
import os
import subprocess
import sys
import tempfile
import pathlib

SCRIPT = pathlib.Path(__file__).parent.parent / "render_handoff_html.py"


def run_render(data):
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(data, f, ensure_ascii=False)
        fname = f.name
    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--input-json", fname],
            capture_output=True,
            text=True,
        )
    finally:
        os.unlink(fname)
    return result


def test_full_input():
    data = {
        "title": "Test",
        "updated": "2026/04/29",
        "sections": [{"header": "S1", "items": ["item1", "item2"]}],
    }
    r = run_render(data)
    assert r.returncode == 0
    assert "<div><b>S1</b></div>" in r.stdout
    assert "<li>item1</li>" in r.stdout
    assert "<li>item2</li>" in r.stdout


def test_empty_sections():
    data = {"title": "Test", "updated": "2026/04/29", "sections": []}
    r = run_render(data)
    assert r.returncode == 0
    assert "<div>Test</div>" in r.stdout


def test_special_chars_escaped():
    data = {
        "title": "A & B",
        "updated": "2026/04/29",
        "sections": [{"header": "H <tag>", "items": ["x > y"]}],
    }
    r = run_render(data)
    assert r.returncode == 0
    assert "&amp;" in r.stdout
    assert "&lt;tag&gt;" in r.stdout
    assert "x &gt; y" in r.stdout


def test_output_file():
    data = {"title": "Out", "updated": "2026/04/29", "sections": []}
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as jf:
        json.dump(data, jf)
        json_file = jf.name
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as hf:
        html_file = hf.name
    try:
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "--input-json", json_file, "--output-file", html_file],
            capture_output=True, text=True,
        )
        assert r.returncode == 0
        content = pathlib.Path(html_file).read_text(encoding="utf-8")
        assert "<div>Out</div>" in content
    finally:
        os.unlink(json_file)
        os.unlink(html_file)
