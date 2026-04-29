#!/usr/bin/env python3
"""Count archive entries and determine if weekly consolidation is needed."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _utils import parse_archive_entries

DEFAULT_THRESHOLD = 5


def main():
    parser = argparse.ArgumentParser(
        description="Count Archive note entries and check consolidation threshold"
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--archive-html", metavar="FILE", help="Read archive HTML from file")
    source.add_argument("--note-title", metavar="TITLE",
                        help="Read archive HTML from Apple Notes (requires applescript_notes.py)")
    args = parser.parse_args()

    threshold = int(os.environ.get("CLAUDE_HANDOFF_ARCHIVE_THRESHOLD", DEFAULT_THRESHOLD))

    if args.archive_html:
        html = Path(args.archive_html).read_text(encoding="utf-8")
    else:
        script_dir = Path(__file__).parent
        result = subprocess.run(
            [sys.executable, str(script_dir / "applescript_notes.py"),
             "read", "--title", args.note_title],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"ERROR: Failed to read note: {result.stderr}", file=sys.stderr)
            sys.exit(1)
        html = result.stdout

    entries = parse_archive_entries(html)
    should_consolidate = len(entries) >= threshold

    output = {
        "count": len(entries),
        "threshold": threshold,
        "should_consolidate": should_consolidate,
        "entries": [
            {"date": e["date"], "agent": e["agent"], "summary": e["summary"]}
            for e in entries
        ],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
