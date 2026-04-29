#!/usr/bin/env python3
"""Validate HTML body for macOS Apple Notes handoff rules."""

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _utils import FORBIDDEN_TAGS, FORBIDDEN_ATTRS_REGEX, count_visible_chars

WHITELIST = {'div', 'b', 'i', 'ul', 'li', 'br', 'tt', 'h1', 'h2', 'h3', 'a', 'span', 'hr'}


class _StrictParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.errors = []
        self._open_tags = []

    def handle_starttag(self, tag, attrs):
        if tag not in WHITELIST:
            self.errors.append(f"ERROR: strict: disallowed tag <{tag}>")
        # void elements don't need closing
        if tag not in ('br', 'hr'):
            self._open_tags.append(tag)

    def handle_endtag(self, tag):
        if self._open_tags and self._open_tags[-1] == tag:
            self._open_tags.pop()

    def get_unclosed(self):
        return self._open_tags[:]


def lint_html(html: str, max_chars: int = 1500, strict: bool = False) -> list:
    errors = []

    for tag in FORBIDDEN_TAGS:
        if tag.lower() in html.lower():
            errors.append(f"ERROR: contains forbidden tag {tag.strip()}")

    if re.search(FORBIDDEN_ATTRS_REGEX, html, re.IGNORECASE):
        errors.append("ERROR: contains forbidden font-size attribute")

    chars = count_visible_chars(html)
    if chars > max_chars:
        errors.append(f"ERROR: {chars} chars exceeds limit of {max_chars}")

    if strict:
        parser = _StrictParser()
        parser.feed(html)
        errors.extend(parser.errors)
        for tag in parser.get_unclosed():
            errors.append(f"ERROR: strict: unclosed tag <{tag}>")

    return errors, chars


def main():
    parser = argparse.ArgumentParser(description="Lint handoff HTML for Apple Notes compatibility")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--html-file", metavar="FILE", help="Read HTML from file")
    source.add_argument("--html-string", metavar="STR", help="HTML string directly")
    parser.add_argument("--max-chars", type=int, default=1500, help="Max visible char count (default 1500)")
    parser.add_argument("--strict", action="store_true", help="Enable strict tag validation")
    args = parser.parse_args()

    if args.html_file:
        html = Path(args.html_file).read_text(encoding="utf-8")
    else:
        html = args.html_string

    errors, chars = lint_html(html, args.max_chars, args.strict)

    if errors:
        for e in errors:
            print(e)
        sys.exit(1)
    else:
        print(f"OK: {chars} chars")
        sys.exit(0)


if __name__ == "__main__":
    main()
