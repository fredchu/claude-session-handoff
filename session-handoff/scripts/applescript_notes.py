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


def cmd_read(title: str, folder: str, account: str):
    esc_title = escape_applescript_str(title)
    esc_folder = escape_applescript_str(folder)
    esc_account = escape_applescript_str(account)
    script = f'''tell application "Notes"
  set targetFolder to first folder of account "{esc_account}" whose name is "{esc_folder}"
  set matchNote to first note of targetFolder whose name contains "{esc_title}"
  return body of matchNote
end tell'''
    body = run_applescript(script)
    print(body)


def cmd_write(title: str, folder: str, account: str, html: str):
    errors = quick_lint(html)
    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        sys.exit(2)

    esc_title = escape_applescript_str(title)
    esc_folder = escape_applescript_str(folder)
    esc_account = escape_applescript_str(account)
    esc_html = escape_applescript_str(html)

    script = f'''tell application "Notes"
  set targetFolder to first folder of account "{esc_account}" whose name is "{esc_folder}"
  set noteBody to "{esc_html}"
  if (count of (notes of targetFolder whose name contains "{esc_title}")) > 0 then
    set matchNote to first note of targetFolder whose name contains "{esc_title}"
    set body of matchNote to noteBody
  else
    make new note at targetFolder with properties {{name:"{esc_title}", body:noteBody}}
  end if
end tell'''
    run_applescript(script)


def cmd_exists(title: str, folder: str, account: str):
    esc_title = escape_applescript_str(title)
    esc_folder = escape_applescript_str(folder)
    esc_account = escape_applescript_str(account)
    script = f'''tell application "Notes"
  set targetFolder to first folder of account "{esc_account}" whose name is "{esc_folder}"
  return (count of (notes of targetFolder whose name contains "{esc_title}")) > 0
end tell'''
    result = run_applescript(script)
    if result == "true":
        sys.exit(0)
    else:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Apple Notes CRUD via AppleScript")
    parser.add_argument("--folder", default="Claude 工作區", help="Notes folder (default: Claude 工作區)")
    parser.add_argument("--account", default="iCloud", help="Notes account (default: iCloud)")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # read subcommand
    read_p = subparsers.add_parser("read", help="Read a note body")
    read_p.add_argument("--title", required=True, help="Note title (partial match)")

    # write subcommand
    write_p = subparsers.add_parser("write", help="Write/update a note")
    write_p.add_argument("--title", required=True, help="Note title")
    html_source = write_p.add_mutually_exclusive_group(required=True)
    html_source.add_argument("--html-file", metavar="FILE", help="HTML file to write")
    html_source.add_argument("--html-string", metavar="STR", help="HTML string to write")

    # exists subcommand
    exists_p = subparsers.add_parser("exists", help="Check if note exists (exit 0=yes, 1=no)")
    exists_p.add_argument("--title", required=True, help="Note title (partial match)")

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


if __name__ == "__main__":
    main()
