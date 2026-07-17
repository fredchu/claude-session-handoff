#!/usr/bin/env python3
"""Move old immutable Archive Markdown entries into weekly directories."""

import argparse
import datetime as dt
import errno
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from markdown_storage import StorageError, scan_archive_entries

DEFAULT_KEEP = 5


def get_iso_week_key(timestamp: str) -> str:
    value = dt.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    year, week, _ = value.isocalendar()
    return f"{year}-W{week:02d}"


def _move_without_overwrite(source: Path, destination: Path) -> None:
    """Move one immutable file, never replacing an existing destination."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(source, destination)
    except FileExistsError as exc:
        raise StorageError(f"consolidation destination already exists: {destination}") from exc
    except OSError as exc:
        if exc.errno != errno.EXDEV:
            raise StorageError(f"failed to move {source}: {exc}") from exc
        try:
            with source.open("rb") as source_handle, destination.open("xb") as destination_handle:
                shutil.copyfileobj(source_handle, destination_handle)
                destination_handle.flush()
                os.fsync(destination_handle.fileno())
        except OSError as copy_exc:
            destination.unlink(missing_ok=True)
            raise StorageError(f"failed to copy {source}: {copy_exc}") from copy_exc
    try:
        source.unlink()
    except OSError as exc:
        raise StorageError(
            f"copied {source} but could not remove source; rerun requires manual duplicate review: {exc}"
        ) from exc


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Move old immutable Archive entries into episodic weekly directories"
    )
    parser.add_argument("--archive-dir", metavar="DIR", required=True,
                        help="Archive directory containing <year>/*.md")
    parser.add_argument("--episodic-dir", metavar="DIR", required=True,
                        help="Destination root for <ISO-week>/<entry>.md")
    parser.add_argument("--keep", type=int, default=DEFAULT_KEEP,
                        help=f"Number of newest entries to keep (default {DEFAULT_KEEP})")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without moving files")
    args = parser.parse_args()

    if args.keep < 0:
        parser.error("--keep must be non-negative")

    try:
        archive_dir = Path(args.archive_dir)
        if archive_dir.name != "Archive":
            raise StorageError("--archive-dir must point to the Archive directory")
        entries = scan_archive_entries(archive_dir.parent)
        promoted = entries[args.keep:]
        plan = [
            (
                entry["path"],
                Path(args.episodic_dir)
                / get_iso_week_key(entry["metadata"]["updated_at"])
                / entry["path"].name,
            )
            for entry in promoted
        ]
        collisions = [destination for _, destination in plan if destination.exists()]
        if collisions:
            raise StorageError(f"refusing to overwrite existing entry: {collisions[0]}")
    except (OSError, StorageError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    weeks = sorted({destination.parent.name for _, destination in plan})
    if args.dry_run:
        print(f"Would move {len(plan)} entries to {weeks}, keep {min(len(entries), args.keep)} in Archive")
        return
    if not plan:
        print(f"nothing to consolidate ({len(entries)} entries <= keep {args.keep}); Archive untouched")
        return

    try:
        for source, destination in plan:
            _move_without_overwrite(source, destination)
    except StorageError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print(f"moved {len(plan)} entries to {weeks}, kept {min(len(entries), args.keep)} in Archive")


if __name__ == "__main__":
    main()
