#!/usr/bin/env python3
"""Count immutable Archive Markdown entries."""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from markdown_storage import StorageError, scan_archive_entries

DEFAULT_THRESHOLD = 5


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Count Archive Markdown entries and check consolidation threshold"
    )
    parser.add_argument("--archive-dir", metavar="DIR", required=True,
                        help="Archive directory containing <year>/*.md")
    args = parser.parse_args()

    try:
        threshold = int(os.environ.get("CLAUDE_HANDOFF_ARCHIVE_THRESHOLD", DEFAULT_THRESHOLD))
        if threshold < 1:
            raise ValueError("threshold must be positive")
        archive_dir = Path(args.archive_dir)
        if archive_dir.name != "Archive":
            raise StorageError("--archive-dir must point to the Archive directory")
        entries = scan_archive_entries(archive_dir.parent)
    except (StorageError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    output = {
        "count": len(entries),
        "threshold": threshold,
        "should_consolidate": len(entries) >= threshold,
        "entries": [
            {
                "updated_at": entry["metadata"]["updated_at"],
                "agent": entry["metadata"]["agent"],
                "session_id": entry["metadata"]["session_id"],
                "path": str(entry["path"]),
            }
            for entry in entries
        ],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
