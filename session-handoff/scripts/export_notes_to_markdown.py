#!/usr/bin/env python3
"""One-time, read-only Apple Notes export into the Markdown handoff store."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).parent))
from _utils import parse_archive_entries
from markdown_storage import (
    StorageError,
    scan_archive_entries,
    write_archive_entry,
    write_shard,
)

DEFAULT_ACTIVE_TITLE = "Session Handoff — Pro CC"
DEFAULT_SHARED_TITLE = "Session Handoff — Shared"
DEFAULT_ARCHIVE_TITLE = "Session Handoff — Archive"


class _MarkdownExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "li":
            self.parts.append("\n- ")
        elif tag in {"br", "div", "ul", "h1", "h2", "h3", "hr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"div", "li", "ul", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def markdown(self) -> str:
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in "".join(self.parts).splitlines()]
        compact: list[str] = []
        for line in lines:
            if line or (compact and compact[-1]):
                compact.append(line)
        return "\n".join(compact).strip()


def html_to_markdown(html: str) -> str:
    # ponytail: preserves text and list boundaries only; add inline link/emphasis handling if audits require it.
    parser = _MarkdownExtractor()
    try:
        parser.feed(html)
        parser.close()
    except Exception as exc:  # HTMLParser can surface malformed character references.
        raise StorageError(f"failed to parse Apple Notes HTML: {exc}") from exc
    markdown = parser.markdown()
    if html.strip() and not markdown:
        raise StorageError("non-empty Apple Notes source produced empty Markdown")
    return markdown


def export_notes(
    root: Path,
    agent: str,
    updated_at: str,
    reader: Callable[[str], str],
    active_title: str | None = None,
    shared_title: str = DEFAULT_SHARED_TITLE,
    archive_title: str = DEFAULT_ARCHIVE_TITLE,
) -> list[Path]:
    """Read all Notes first, then export; the reader is injectable for tmp-only tests."""
    active_title = active_title or f"Session Handoff — {agent}"
    active_html = reader(active_title)
    shared_html = reader(shared_title)
    archive_html = reader(archive_title)

    active_body = html_to_markdown(active_html)
    shared_body = html_to_markdown(shared_html)
    legacy_entries = parse_archive_entries(archive_html)
    dated_headers = 0
    for raw_div in re.findall(
        r"<div(?:\s[^>]*)?>(.*?)</div>", archive_html, re.DOTALL | re.IGNORECASE
    ):
        text = html.unescape(re.sub(r"<[^>]+>", "", raw_div)).strip()
        dated_headers += bool(re.match(r"^\d{4}/\d{2}/\d{2}\b", text))
    if dated_headers != len(legacy_entries):
        raise StorageError(
            f"Archive parse mismatch: found {dated_headers} dated headers but parsed {len(legacy_entries)}"
        )
    archive_rows = []
    local_zone = dt.datetime.now().astimezone().tzinfo
    for entry in legacy_entries:
        body = html_to_markdown(entry["raw"])
        digest = hashlib.sha256(entry["raw"].encode("utf-8")).hexdigest()
        timestamp = dt.datetime.strptime(entry["date"], "%Y/%m/%d").replace(tzinfo=local_zone)
        archive_rows.append({
            "agent": entry["agent"],
            "session_id": f"apple-notes-{digest}",
            "slug": f"{entry['summary']}-{digest[:8]}",
            "body": body,
            "updated_at": timestamp.isoformat(),
        })

    # Validate the complete destination before replacing either mutable shard.
    scan_archive_entries(root)
    written = [
        write_shard(root, "active", agent, agent, active_body, updated_at),
        write_shard(root, "shared", agent, agent, shared_body, updated_at),
    ]
    for row in archive_rows:
        path, _ = write_archive_entry(root, **row)
        written.append(path)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Apple Notes handoffs to Markdown")
    parser.add_argument("--root", type=Path, required=True, help="Markdown storage root")
    parser.add_argument("--agent", required=True, help="Owner of exported Active and Shared shards")
    parser.add_argument("--updated-at", help="ISO timestamp for Active and Shared (default: now)")
    parser.add_argument("--active-title", help="Active note title (default: Session Handoff — <agent>)")
    parser.add_argument("--shared-title", default=DEFAULT_SHARED_TITLE)
    parser.add_argument("--archive-title", default=DEFAULT_ARCHIVE_TITLE)
    parser.add_argument("--folder", default="Claude 工作區")
    parser.add_argument("--account", default="iCloud")
    args = parser.parse_args()

    script = Path(__file__).parent / "applescript_notes.py"

    def read_note(title: str) -> str:
        result = subprocess.run(
            [sys.executable, str(script), "--folder", args.folder, "--account", args.account,
             "read", "--title", title],
            capture_output=True,
            text=True,
        )
        if result.returncode:
            raise StorageError(f"failed to read Apple Note {title!r}: {result.stderr.strip()}")
        return result.stdout

    try:
        paths = export_notes(
            args.root,
            args.agent,
            args.updated_at or dt.datetime.now().astimezone().isoformat(),
            read_note,
            args.active_title,
            args.shared_title,
            args.archive_title,
        )
    except StorageError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print(f"exported {len(paths)} Markdown files; Apple Notes were read only")


if __name__ == "__main__":
    main()
