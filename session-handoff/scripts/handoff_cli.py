#!/usr/bin/env python3
"""Deterministic CLI over markdown_storage — the only supported write path for handoffs.

Subcommands:
  write    --root R --kind active|shared --agent A --body-file F [--updated-at ISO]
  archive  --root R --agent A --slug S --body-file F [--updated-at ISO]
  session-start --root R --agent A [--active-budget N] [--shared-budget N]
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from markdown_storage import (
    StorageError,
    compose_session_start,
    write_archive_entry,
    write_shard,
)


def _now() -> str:
    return dt.datetime.now().astimezone().isoformat()


def cmd_write(args: argparse.Namespace) -> None:
    body = Path(args.body_file).read_text()
    path = write_shard(args.root, args.kind, args.agent, args.agent, body, args.updated_at or _now())
    print(f"wrote {path}")


def cmd_archive(args: argparse.Namespace) -> None:
    body = Path(args.body_file).read_text()
    path, created = write_archive_entry(
        args.root, args.agent, args.session_id, args.slug, body, args.updated_at or _now()
    )
    print(f"{'wrote' if created else 'exists (dedup by session_id)'} {path}")


def cmd_session_start(args: argparse.Namespace) -> None:
    try:
        result = compose_session_start(
            args.root, args.agent,
            shared_budget=args.shared_budget,
            stale_after=dt.timedelta(days=args.stale_days),
        )
    except FileNotFoundError:
        print("ℹ️ 沒有 Session Handoff 記錄")
        return
    active = result["active"]
    body = active["body"].strip()
    if len(body) > args.active_budget:
        body = body[: args.active_budget] + "\n[truncated]"
    stale = "（⚠️ stale）" if active.get("stale") else ""
    print(f"Session Handoff — {args.agent} (updated: {active['metadata']['updated_at']}){stale}:")
    print(body)
    for doc in result["shared"]:
        print()
        print(f"Session Handoff — Shared [{doc['metadata']['agent']}] "
              f"(updated: {doc['metadata']['updated_at']}){'（⚠️ stale）' if doc.get('stale') else ''}:")
        print(doc["body"].strip())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("write", help="Upsert an Active/Shared shard")
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--kind", choices=["active", "shared"], required=True)
    p.add_argument("--agent", required=True)
    p.add_argument("--body-file", required=True)
    p.add_argument("--updated-at")
    p.set_defaults(func=cmd_write)

    p = sub.add_parser("archive", help="Append an Archive entry")
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--agent", required=True)
    p.add_argument("--session-id", required=True, help="Stable id for idempotent re-runs (e.g. date+topic)")
    p.add_argument("--slug", required=True)
    p.add_argument("--body-file", required=True)
    p.add_argument("--updated-at")
    p.set_defaults(func=cmd_archive)

    p = sub.add_parser("session-start", help="Print SessionStart context (active + shared)")
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--agent", required=True)
    p.add_argument("--active-budget", type=int, default=1800)
    p.add_argument("--shared-budget", type=int, default=1200)
    p.add_argument("--stale-days", type=int, default=14)
    p.set_defaults(func=cmd_session_start)

    args = parser.parse_args()
    try:
        args.func(args)
    except StorageError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
