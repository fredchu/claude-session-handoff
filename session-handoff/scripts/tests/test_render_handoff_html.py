import json
import pathlib
import subprocess
import sys

from markdown_storage import parse_markdown

SCRIPT = pathlib.Path(__file__).parent.parent / "render_handoff_html.py"


def run_render(tmp_path, data, output=None):
    source = tmp_path / "input.json"
    source.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    args = [sys.executable, str(SCRIPT), "--input-json", str(source)]
    if output:
        args += ["--output-file", str(output)]
    return subprocess.run(args, capture_output=True, text=True)


def valid_data():
    return {
        "kind": "active",
        "agent": "Pro CC",
        "updated_at": "2026-07-17T10:00:00+08:00",
        "title": "Current work",
        "sections": [{"header": "Next", "items": ["item 1", "item 2"]}],
    }


def test_renders_schema_valid_markdown(tmp_path):
    result = run_render(tmp_path, valid_data())
    assert result.returncode == 0
    metadata, body = parse_markdown(result.stdout, "active")
    assert metadata["agent"] == "Pro CC"
    assert "# Current work" in body
    assert "## Next\n- item 1\n- item 2" in body


def test_output_file_is_markdown(tmp_path):
    output = tmp_path / "Active" / "Pro CC.md"
    result = run_render(tmp_path, valid_data(), output)
    assert result.returncode == 0
    metadata, _ = parse_markdown(output.read_text(encoding="utf-8"), "active")
    assert metadata["schema_version"] == 1


def test_missing_schema_field_fails(tmp_path):
    data = valid_data()
    del data["agent"]
    result = run_render(tmp_path, data)
    assert result.returncode == 2
    assert "missing frontmatter fields: agent" in result.stderr
