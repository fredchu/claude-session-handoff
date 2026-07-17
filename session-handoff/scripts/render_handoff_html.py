#!/usr/bin/env python3
"""Render a schema-valid handoff Markdown document from JSON."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from markdown_storage import SCHEMA_VERSION, SchemaError, atomic_write_text, render_markdown


def _line(value: object) -> str:
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def render_handoff(data: dict) -> str:
    """Render the existing title/sections JSON shape as Markdown plus frontmatter."""
    metadata = {
        "schema_version": SCHEMA_VERSION,
        "kind": data.get("kind"),
        "agent": data.get("agent"),
        "updated_at": data.get("updated_at"),
    }
    if data.get("session_id"):
        metadata["session_id"] = data["session_id"]

    body = []
    if data.get("title"):
        body.append(f"# {_line(data['title'])}")
    for section in data.get("sections", []):
        body.extend(["", f"## {_line(section.get('header', ''))}"])
        body.extend(f"- {_line(item)}" for item in section.get("items", []))
    return render_markdown(metadata, "\n".join(body).strip())


def main() -> None:
    parser = argparse.ArgumentParser(description="Render handoff Markdown from JSON structure")
    parser.add_argument("--input-json", metavar="FILE", required=True,
                        help="JSON input file (use '-' for stdin)")
    parser.add_argument("--output-file", metavar="FILE",
                        help="Output file (default: stdout)")
    args = parser.parse_args()

    try:
        if args.input_json == "-":
            data = json.load(sys.stdin)
        else:
            data = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
        markdown = render_handoff(data)
        if args.output_file:
            atomic_write_text(Path(args.output_file), markdown)
        else:
            print(markdown, end="")
    except (OSError, UnicodeError, json.JSONDecodeError, SchemaError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
