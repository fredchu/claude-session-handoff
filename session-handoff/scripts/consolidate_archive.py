#!/usr/bin/env python3
"""Execute weekly consolidation: promote old archive entries to episodic files."""

import argparse
import datetime
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _utils import parse_archive_entries, run_applescript, escape_applescript_str

DEFAULT_KEEP = 5
DEFAULT_NOTE_TITLE = "Session Handoff — Archive"


def sort_entries_by_date(entries: list) -> list:
    """Sort entries newest first."""
    def parse_date(e):
        try:
            return datetime.datetime.strptime(e["date"], "%Y/%m/%d")
        except ValueError:
            return datetime.datetime.min
    return sorted(entries, key=parse_date, reverse=True)


def get_iso_week_key(date_str: str) -> str:
    """Return 'YYYY-WNN' for a date string 'YYYY/MM/DD'."""
    dt = datetime.datetime.strptime(date_str, "%Y/%m/%d")
    iso = dt.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def write_episodic_file(episodic_dir: Path, week_key: str, entries: list):
    """Write or append entries to the episodic weekly report file."""
    filename = episodic_dir / f"{week_key}-weekly-report.md"
    if filename.exists():
        with filename.open("a", encoding="utf-8") as f:
            for entry in entries:
                f.write(f"\n## 補錄 [Pro CC] {entry['date']}\n{entry['raw']}\n")
    else:
        with filename.open("w", encoding="utf-8") as f:
            f.write(f"# Weekly Report {week_key}\n\n")
            for entry in entries:
                f.write(f"{entry['raw']}\n")


def rebuild_archive_html(note_title: str, kept_entries: list) -> str:
    """Rebuild archive HTML from kept entries."""
    parts = [
        f"<div>{note_title}</div>",
        "<div><i>歷史 handoff 歸檔（最新在上）</i><br></div>",
        "<div><br></div>",
    ]
    parts.extend(e["raw"].rstrip() for e in kept_entries)
    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(
        description="Consolidate old archive entries into episodic weekly reports"
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--archive-html", metavar="FILE",
                        help="Read archive HTML from file (writes back to same file unless dry-run)")
    source.add_argument("--apply", action="store_true",
                        help="Read/write directly from Apple Notes")

    parser.add_argument("--episodic-dir", metavar="DIR",
                        help="Output directory for episodic weekly reports")
    parser.add_argument("--keep", type=int, default=DEFAULT_KEEP,
                        help=f"Number of newest entries to keep (default {DEFAULT_KEEP})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print plan without writing any files")
    parser.add_argument("--note-title", default=DEFAULT_NOTE_TITLE,
                        help=f"Archive note title (default: '{DEFAULT_NOTE_TITLE}')")
    args = parser.parse_args()

    if not args.episodic_dir:
        parser.error("--episodic-dir is required (promoted entries must be written somewhere)")

    # Read archive HTML
    if args.apply:
        script_dir = Path(__file__).parent
        result = subprocess.run(
            [sys.executable, str(script_dir / "applescript_notes.py"),
             "read", "--title", args.note_title],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"ERROR: {result.stderr}", file=sys.stderr)
            sys.exit(1)
        html = result.stdout
    else:
        html = Path(args.archive_html).read_text(encoding="utf-8")

    entries = parse_archive_entries(html)
    sorted_entries = sort_entries_by_date(entries)

    kept = sorted_entries[:args.keep]
    promoted = sorted_entries[args.keep:]

    # Group promoted entries by ISO week
    week_groups: dict = {}
    for entry in promoted:
        week_key = get_iso_week_key(entry["date"])
        week_groups.setdefault(week_key, []).append(entry)

    week_list = sorted(week_groups.keys())

    if args.dry_run:
        print(f"Would promote {len(promoted)} entries to {week_list}, keep {len(kept)} in archive")
        return

    # ponytail: local substantive-source heuristic; upgrade by returning parser/read status.
    if not entries and html.strip() and (
        len(html.strip()) > len(rebuild_archive_html(args.note_title, []).strip())
        or re.search(r"<b>\d{4}/\d{2}/\d{2}", html)
    ):
        print(
            "refusing to rewrite archive: parsed 0 entries from non-empty source — likely "
            "a read race or parse failure; archive left untouched",
            file=sys.stderr,
        )
        sys.exit(1)

    if not promoted:
        print(f"nothing to consolidate ({len(entries)} entries <= keep {args.keep}); archive untouched")
        return

    # Write episodic files
    episodic_dir = Path(args.episodic_dir)
    episodic_dir.mkdir(parents=True, exist_ok=True)
    for week_key, week_entries in week_groups.items():
        write_episodic_file(episodic_dir, week_key, week_entries)

    # Rebuild archive
    new_archive_html = rebuild_archive_html(args.note_title, kept)

    if args.apply:
        script_dir = Path(__file__).parent
        subprocess.run(
            [sys.executable, str(script_dir / "applescript_notes.py"),
             "write", "--title", args.note_title, "--html-string", new_archive_html],
            check=True
        )
    else:
        Path(args.archive_html).write_text(new_archive_html, encoding="utf-8")

    print(f"promoted {len(promoted)} entries to {week_list}, kept {len(kept)} in archive")


if __name__ == "__main__":
    main()
