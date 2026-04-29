#!/usr/bin/env python3
"""Render a handoff HTML body from a JSON structure."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _utils import FORBIDDEN_TAGS, FORBIDDEN_ATTRS_REGEX, count_visible_chars
import re


def escape_html(text: str) -> str:
    """Escape HTML special characters in text content."""
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text


def render_html(data: dict) -> str:
    """Render handoff HTML from structured data dict."""
    lines = []

    title = escape_html(data.get("title", ""))
    updated = escape_html(data.get("updated", ""))

    lines.append(f"<div>{title}</div>")
    lines.append(f"<div><i>更新時間：{updated}</i></div>")
    lines.append("<div><br></div>")

    for section in data.get("sections", []):
        header = escape_html(section.get("header", ""))
        items = section.get("items", [])
        lines.append(f"<div><b>{header}</b></div>")
        item_html = "".join(f"<li>{escape_html(item)}</li>" for item in items)
        lines.append(f"<ul>{item_html}</ul>")
        lines.append("<div><br></div>")

    return "\n".join(lines)


def quick_lint(html: str) -> list:
    """Quick lint: check FORBIDDEN_TAGS and FORBIDDEN_ATTRS_REGEX."""
    errors = []
    for tag in FORBIDDEN_TAGS:
        if tag.lower() in html.lower():
            errors.append(f"ERROR: contains forbidden tag {tag.strip()}")
    if re.search(FORBIDDEN_ATTRS_REGEX, html, re.IGNORECASE):
        errors.append("ERROR: contains forbidden font-size attribute")
    return errors


def main():
    parser = argparse.ArgumentParser(description="Render handoff HTML from JSON structure")
    parser.add_argument("--input-json", metavar="FILE", required=True,
                        help="JSON input file (use '-' for stdin)")
    parser.add_argument("--output-file", metavar="FILE",
                        help="Output file (default: stdout)")
    args = parser.parse_args()

    if args.input_json == "-":
        data = json.load(sys.stdin)
    else:
        data = json.loads(Path(args.input_json).read_text(encoding="utf-8"))

    html = render_html(data)

    errors = quick_lint(html)
    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        sys.exit(2)

    if args.output_file:
        Path(args.output_file).write_text(html, encoding="utf-8")
    else:
        print(html)


if __name__ == "__main__":
    main()
