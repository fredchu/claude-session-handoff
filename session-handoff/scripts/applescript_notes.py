#!/usr/bin/env python3
"""Apple Notes CRUD operations via AppleScript."""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _utils import escape_applescript_str, run_applescript, FORBIDDEN_TAGS, FORBIDDEN_ATTRS_REGEX


def quick_lint(html: str) -> list:
    """Quick lint: check FORBIDDEN_TAGS and FORBIDDEN_ATTRS_REGEX."""
    errors = []
    for tag in FORBIDDEN_TAGS:
        if tag.lower() in html.lower():
            errors.append(f"ERROR: contains forbidden tag {tag.strip()}")
    if re.search(FORBIDDEN_ATTRS_REGEX, html, re.IGNORECASE):
        errors.append("ERROR: contains forbidden font-size attribute")
    return errors


def build_read_script(title: str, folder: str, account: str) -> str:
    esc_title = escape_applescript_str(title)
    esc_folder = escape_applescript_str(folder)
    esc_account = escape_applescript_str(account)
    return f'''tell application "Notes"
  set targetFolder to first folder of account "{esc_account}" whose name is "{esc_folder}"
  set matchNote to first note of targetFolder whose name is "{esc_title}"
  return body of matchNote
end tell'''


def build_write_script(title: str, folder: str, account: str, html: str) -> str:
    esc_title = escape_applescript_str(title)
    esc_folder = escape_applescript_str(folder)
    esc_account = escape_applescript_str(account)
    esc_html = escape_applescript_str(html)

    return f'''tell application "Notes"
  set targetFolder to first folder of account "{esc_account}" whose name is "{esc_folder}"
  set noteBody to "{esc_html}"
  if (count of (notes of targetFolder whose name is "{esc_title}")) > 0 then
    set matchNote to first note of targetFolder whose name is "{esc_title}"
    set body of matchNote to noteBody
  else
    make new note at targetFolder with properties {{name:"{esc_title}", body:noteBody}}
  end if
end tell'''


def build_exists_script(title: str, folder: str, account: str) -> str:
    esc_title = escape_applescript_str(title)
    esc_folder = escape_applescript_str(folder)
    esc_account = escape_applescript_str(account)
    return f'''tell application "Notes"
  set targetFolder to first folder of account "{esc_account}" whose name is "{esc_folder}"
  return (count of (notes of targetFolder whose name is "{esc_title}")) > 0
end tell'''


def build_dedup_list_script(title: str, folder: str, account: str) -> str:
    esc_title = escape_applescript_str(title)
    esc_folder = escape_applescript_str(folder)
    esc_account = escape_applescript_str(account)
    # Emit a locale-independent fixed-width YYYYMMDDHHMMSS sort key alongside the
    # human-readable date. Sorting the localized "2026年5月6日…" string directly is
    # chronologically wrong (e.g. "5月6日" sorts after "5月29日"), which would make
    # --apply delete the newest note instead of the oldest.
    return f'''on pad2(n)
  set s to (n as integer) as text
  if (length of s) < 2 then set s to "0" & s
  return s
end pad2
tell application "Notes"
  set targetFolder to first folder of account "{esc_account}" whose name is "{esc_folder}"
  set matchedNotes to notes of targetFolder whose name is "{esc_title}"
  set outputLines to {{}}
  repeat with matchNote in matchedNotes
    set d to modification date of matchNote
    set sortKey to ((year of d) as text) & my pad2((month of d) as integer) & my pad2(day of d) & my pad2(hours of d) & my pad2(minutes of d) & my pad2(seconds of d)
    set end of outputLines to (id of matchNote as text) & tab & sortKey & tab & (d as text)
  end repeat
  set AppleScript's text item delimiters to linefeed
  set outputText to outputLines as text
  set AppleScript's text item delimiters to ""
  return outputText
end tell'''


def build_dedup_delete_script(note_ids: list) -> str:
    quoted_ids = ", ".join(f'"{escape_applescript_str(note_id)}"' for note_id in note_ids)
    # Wrap each delete in try so the script is idempotent: if run_applescript
    # retries a transient failure after some deletes already landed, the
    # already-gone ids simply no-op instead of raising "can't get note id …".
    return f'''tell application "Notes"
  set noteIdsToDelete to {{{quoted_ids}}}
  repeat with noteIdToDelete in noteIdsToDelete
    try
      delete first note whose id is (noteIdToDelete as text)
    end try
  end repeat
end tell'''


def _parse_dedup_rows(output: str) -> list:
    rows = []
    for line in output.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        rows.append({
            "id": parts[0].strip() if len(parts) > 0 else "",
            "sort_key": parts[1].strip() if len(parts) > 1 else "",
            "modified_at": parts[2].strip() if len(parts) > 2 else "",
        })
    return rows


def _sort_dedup_rows(rows: list) -> list:
    """Newest first by locale-independent fixed-width sort key (not the display date).

    Secondary key is the note id, so same-second ties resolve deterministically
    (same choice every run) — required for the auto-run hook to be idempotent.
    """
    return sorted(rows, key=lambda note: (note["sort_key"], note["id"]), reverse=True)


def cmd_read(title: str, folder: str, account: str):
    script = build_read_script(title, folder, account)
    body = run_applescript(script)
    print(body)


def cmd_write(title: str, folder: str, account: str, html: str):
    errors = quick_lint(html)
    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        sys.exit(2)

    script = build_write_script(title, folder, account, html)
    run_applescript(script)


def cmd_exists(title: str, folder: str, account: str):
    script = build_exists_script(title, folder, account)
    result = run_applescript(script)
    if result == "true":
        sys.exit(0)
    else:
        sys.exit(1)


def cmd_dedup(title: str, folder: str, account: str, apply: bool):
    output = run_applescript(build_dedup_list_script(title, folder, account))
    notes = _sort_dedup_rows(_parse_dedup_rows(output))

    if len(notes) <= 1:
        print(f"OK: {len(notes)} note(s)")
        return

    if not apply:
        print(f"Found {len(notes)} duplicate notes newest-first:")
        for note in notes:
            print(f"{note['id']}\t{note['modified_at']}")
        print("Hint: rerun with --apply to keep newest and delete the rest.")
        return

    keep = notes[0]
    delete_ids = [note["id"] for note in notes[1:]]
    run_applescript(build_dedup_delete_script(delete_ids))
    print(f"Kept newest note: {keep['id']}\t{keep['modified_at']}")
    for note_id in delete_ids:
        print(f"Deleted: {note_id}")


def main():
    parser = argparse.ArgumentParser(description="Apple Notes CRUD via AppleScript")
    parser.add_argument("--folder", default="Claude 工作區", help="Notes folder (default: Claude 工作區)")
    parser.add_argument("--account", default="iCloud", help="Notes account (default: iCloud)")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # read subcommand
    read_p = subparsers.add_parser("read", help="Read a note body")
    read_p.add_argument("--title", required=True, help="Note title")

    # write subcommand
    write_p = subparsers.add_parser("write", help="Write/update a note")
    write_p.add_argument("--title", required=True, help="Note title")
    html_source = write_p.add_mutually_exclusive_group(required=True)
    html_source.add_argument("--html-file", metavar="FILE", help="HTML file to write")
    html_source.add_argument("--html-string", metavar="STR", help="HTML string to write")

    # exists subcommand
    exists_p = subparsers.add_parser("exists", help="Check if note exists (exit 0=yes, 1=no)")
    exists_p.add_argument("--title", required=True, help="Note title")

    # dedup subcommand
    dedup_p = subparsers.add_parser("dedup", help="List or delete duplicate exact-title notes")
    dedup_p.add_argument("--title", required=True, help="Note title")
    dedup_p.add_argument("--apply", action="store_true", help="Keep newest note and delete duplicates")

    args = parser.parse_args()

    if args.command == "read":
        cmd_read(args.title, args.folder, args.account)
    elif args.command == "write":
        if args.html_file:
            html = Path(args.html_file).read_text(encoding="utf-8")
        else:
            html = args.html_string
        cmd_write(args.title, args.folder, args.account, html)
    elif args.command == "exists":
        cmd_exists(args.title, args.folder, args.account)
    elif args.command == "dedup":
        cmd_dedup(args.title, args.folder, args.account, args.apply)


if __name__ == "__main__":
    main()
