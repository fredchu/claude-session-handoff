#!/usr/bin/env python3
"""Lint handoff Markdown frontmatter, size, and freshness."""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from markdown_storage import SchemaError, parse_markdown


def lint_markdown(
    markdown: str,
    max_chars: int = 1500,
    expected_kind: str | None = None,
    stale_after_hours: float | None = None,
    now: dt.datetime | None = None,
) -> tuple[list[str], list[str], int]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        metadata, body = parse_markdown(markdown, expected_kind)
    except SchemaError as exc:
        return [f"ERROR: {exc}"], warnings, 0

    chars = len(body.strip())
    if chars > max_chars:
        errors.append(f"ERROR: {chars} chars exceeds limit of {max_chars}")
    if stale_after_hours is not None:
        updated = dt.datetime.fromisoformat(metadata["updated_at"].replace("Z", "+00:00"))
        current = now or dt.datetime.now().astimezone()
        age = current.astimezone(dt.timezone.utc) - updated.astimezone(dt.timezone.utc)
        if age > dt.timedelta(hours=stale_after_hours):
            warnings.append(
                f"WARNING: stale handoff from {metadata['updated_at']} ({age.total_seconds() / 3600:.1f}h old)"
            )
    return errors, warnings, chars


def main() -> None:
    parser = argparse.ArgumentParser(description="Lint handoff Markdown schema and size")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--markdown-file", metavar="FILE", help="Read Markdown from file")
    source.add_argument("--markdown-string", metavar="STR", help="Lint a Markdown string")
    parser.add_argument("--max-chars", type=int, default=1500,
                        help="Max body character count (default 1500)")
    parser.add_argument("--kind", choices=("active", "shared", "archive"),
                        help="Require this frontmatter kind")
    parser.add_argument("--stale-after-hours", type=float,
                        help="Warn when updated_at is older than this many hours")
    args = parser.parse_args()

    try:
        markdown = (Path(args.markdown_file).read_text(encoding="utf-8")
                    if args.markdown_file else args.markdown_string)
    except (OSError, UnicodeError) as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1) from exc

    errors, warnings, chars = lint_markdown(
        markdown, args.max_chars, args.kind, args.stale_after_hours
    )
    for message in errors + warnings:
        print(message)
    if errors:
        raise SystemExit(1)
    print(f"OK: {chars} chars")


if __name__ == "__main__":
    main()
