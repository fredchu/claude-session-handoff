#!/usr/bin/env python3
"""Filesystem storage for agent-owned Markdown handoffs."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import tempfile
import unicodedata
from pathlib import Path

SCHEMA_VERSION = 1
KINDS = {"active", "shared", "archive"}
REQUIRED_FIELDS = {"schema_version", "kind", "agent", "updated_at"}


class StorageError(RuntimeError):
    """Raised when a handoff cannot be read or written safely."""


class SchemaError(StorageError):
    """Raised when Markdown frontmatter is absent or invalid."""


def _safe_component(value: str, label: str) -> str:
    if not isinstance(value, str):
        raise StorageError(f"invalid {label}")
    value = value.strip()
    if not value or value in {".", ".."}:
        raise StorageError(f"invalid {label}")
    if any(char in value for char in ("/", "\\", "\0")) or any(ord(char) < 32 for char in value):
        raise StorageError(f"unsafe {label}: {value!r}")
    return value


def _inside(root: Path, target: Path) -> Path:
    root = root.expanduser().resolve()
    target = target.expanduser().resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise StorageError(f"path escapes storage root: {target}") from exc
    return target


def _parse_timestamp(value: str) -> dt.datetime:
    if not isinstance(value, str):
        raise SchemaError(f"invalid updated_at: {value!r}")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise SchemaError(f"invalid updated_at: {value!r}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SchemaError("updated_at must include a UTC offset")
    return parsed


def validate_metadata(metadata: dict, expected_kind: str | None = None) -> dict:
    missing = {key for key in REQUIRED_FIELDS if metadata.get(key) in (None, "")}
    if missing:
        raise SchemaError(f"missing frontmatter fields: {', '.join(sorted(missing))}")
    if metadata["schema_version"] != SCHEMA_VERSION:
        raise SchemaError(f"unsupported schema_version: {metadata['schema_version']!r}")
    if metadata["kind"] not in KINDS:
        raise SchemaError(f"invalid kind: {metadata['kind']!r}")
    if expected_kind and metadata["kind"] != expected_kind:
        raise SchemaError(f"expected kind {expected_kind!r}, got {metadata['kind']!r}")
    try:
        _safe_component(metadata["agent"], "agent")
    except StorageError as exc:
        raise SchemaError(str(exc)) from exc
    _parse_timestamp(metadata["updated_at"])
    if metadata["kind"] == "archive" and not metadata.get("session_id"):
        raise SchemaError("archive frontmatter requires session_id")
    return metadata


def parse_markdown(text: str, expected_kind: str | None = None) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        raise SchemaError("missing frontmatter opening delimiter")
    if text.startswith("---\n---\n"):
        raise SchemaError("empty frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise SchemaError("missing frontmatter closing delimiter")

    # ponytail: schema v1 supports flat scalar frontmatter only; use a YAML parser if nesting is added.
    metadata: dict = {}
    frontmatter = text[4:end]
    if not frontmatter.strip():
        raise SchemaError("empty frontmatter")
    for line in frontmatter.splitlines():
        if ":" not in line:
            raise SchemaError(f"invalid frontmatter line: {line!r}")
        key, raw_value = line.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if not key or key in metadata or not raw_value:
            raise SchemaError(f"invalid frontmatter field: {key!r}")
        if raw_value.startswith('"'):
            try:
                value = json.loads(raw_value)
            except json.JSONDecodeError as exc:
                raise SchemaError(f"invalid quoted value for {key}") from exc
        elif key == "schema_version":
            try:
                value = int(raw_value)
            except ValueError as exc:
                raise SchemaError("schema_version must be an integer") from exc
        else:
            value = raw_value
        metadata[key] = value

    return validate_metadata(metadata, expected_kind), text[end + 5 :]


def render_markdown(metadata: dict, body: str) -> str:
    validate_metadata(metadata)
    ordered = ["schema_version", "kind", "agent", "updated_at"]
    ordered.extend(key for key in metadata if key not in ordered)
    lines = ["---"]
    for key in ordered:
        value = metadata[key]
        rendered = str(value) if isinstance(value, int) else json.dumps(value, ensure_ascii=False)
        lines.append(f"{key}: {rendered}")
    lines.extend(["---", body.rstrip(), ""])
    return "\n".join(lines)


def atomic_write_text(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    except OSError as exc:
        raise StorageError(f"atomic write failed for {path}: {exc}") from exc
    finally:
        if temp_path:
            temp_path.unlink(missing_ok=True)


def _atomic_create(path: Path, text: str) -> bool:
    """Create an immutable entry atomically; return False if it already exists."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temp_path, path)
        except FileExistsError:
            return False
        return True
    except OSError as exc:
        raise StorageError(f"immutable write failed for {path}: {exc}") from exc
    finally:
        if temp_path:
            temp_path.unlink(missing_ok=True)


def read_document(path: Path, expected_kind: str | None = None) -> dict:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise StorageError(f"failed to read {path}: {exc}") from exc
    metadata, body = parse_markdown(text, expected_kind)
    return {"path": Path(path), "metadata": metadata, "body": body}


def shard_path(root: Path, kind: str, agent: str) -> Path:
    if kind not in {"active", "shared"}:
        raise StorageError("shard kind must be active or shared")
    safe_agent = _safe_component(agent, "agent")
    return _inside(Path(root), Path(root) / kind.capitalize() / f"{safe_agent}.md")


def write_shard(
    root: Path, kind: str, agent: str, writer_agent: str, body: str, updated_at: str
) -> Path:
    safe_agent = _safe_component(agent, "agent")
    if _safe_component(writer_agent, "writer agent") != safe_agent:
        raise StorageError(f"{writer_agent!r} cannot overwrite {agent!r} {kind} shard")
    metadata = {
        "schema_version": SCHEMA_VERSION,
        "kind": kind,
        "agent": safe_agent,
        "updated_at": updated_at,
    }
    path = shard_path(root, kind, safe_agent)
    atomic_write_text(path, render_markdown(metadata, body))
    return path


def read_shard(
    root: Path,
    kind: str,
    agent: str,
    stale_after: dt.timedelta | None = None,
    now: dt.datetime | None = None,
) -> dict:
    document = read_document(shard_path(root, kind, agent), kind)
    document["stale"] = False
    if stale_after is not None:
        current = now or dt.datetime.now().astimezone()
        updated = _parse_timestamp(document["metadata"]["updated_at"])
        document["stale"] = current.astimezone(dt.timezone.utc) - updated.astimezone(dt.timezone.utc) > stale_after
    return document


def compose_session_start(
    root: Path,
    agent: str,
    shared_budget: int = 1000,
    stale_after: dt.timedelta | None = None,
    now: dt.datetime | None = None,
) -> dict:
    """Load the agent's Active plus every Shared shard within one total body budget."""
    if shared_budget < 0:
        raise StorageError("shared_budget must be non-negative")
    active = read_shard(root, "active", agent, stale_after, now)
    shared_root = _inside(Path(root), Path(root) / "Shared")
    if not shared_root.exists():
        return {"active": active, "shared": [], "shared_truncated": False}
    placeholders = sorted(shared_root.glob("*.icloud"))
    if placeholders:
        raise StorageError(f"iCloud placeholder is not readable: {placeholders[0]}")

    shared = []
    for path in sorted(shared_root.glob("*.md")):
        path = _inside(Path(root), path)
        document = read_document(path, "shared")
        if path.stem != document["metadata"]["agent"]:
            raise SchemaError(f"Shared filename/agent mismatch: {path}")
        updated = _parse_timestamp(document["metadata"]["updated_at"])
        current = now or dt.datetime.now().astimezone()
        document["stale"] = bool(
            stale_after
            and current.astimezone(dt.timezone.utc) - updated.astimezone(dt.timezone.utc) > stale_after
        )
        shared.append(document)

    total = sum(len(document["body"].strip()) for document in shared)
    truncated = total > shared_budget
    if truncated and shared:
        per_shard, remainder = divmod(shared_budget, len(shared))
        for index, document in enumerate(shared):
            limit = per_shard + (1 if index < remainder else 0)
            document["body"] = document["body"].strip()[:limit]
    return {"active": active, "shared": shared, "shared_truncated": truncated}


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return slug[:80] or "handoff"


def archive_filename(updated_at: str, agent: str, slug: str) -> str:
    timestamp = _parse_timestamp(updated_at).strftime("%Y-%m-%dT%H%M%S%z")
    return f"{timestamp}--{slugify(agent)}--{slugify(slug)}.md"


def scan_archive_entries(root: Path) -> list[dict]:
    archive_root = _inside(Path(root), Path(root) / "Archive")
    if not archive_root.exists():
        return []
    placeholders = sorted(archive_root.rglob("*.icloud"))
    if placeholders:
        raise StorageError(f"iCloud placeholder is not readable: {placeholders[0]}")
    entries = []
    for path in sorted(archive_root.rglob("*.md")):
        path = _inside(Path(root), path)
        document = read_document(path, "archive")
        year = str(_parse_timestamp(document["metadata"]["updated_at"]).year)
        if path.parent.name != year:
            raise SchemaError(f"archive year mismatch: {path}")
        entries.append(document)
    entries.sort(key=lambda entry: _parse_timestamp(entry["metadata"]["updated_at"]), reverse=True)
    return entries


def write_archive_entry(
    root: Path,
    agent: str,
    session_id: str,
    slug: str,
    body: str,
    updated_at: str,
) -> tuple[Path, bool]:
    agent = _safe_component(agent, "agent")
    session_id = _safe_component(session_id, "session_id")
    for entry in scan_archive_entries(root):
        metadata = entry["metadata"]
        if metadata["agent"] == agent and metadata.get("session_id") == session_id:
            return entry["path"], False

    parsed_time = _parse_timestamp(updated_at)
    filename = archive_filename(updated_at, agent, slug)
    path = _inside(Path(root), Path(root) / "Archive" / str(parsed_time.year) / filename)
    metadata = {
        "schema_version": SCHEMA_VERSION,
        "kind": "archive",
        "agent": agent,
        "updated_at": updated_at,
        "session_id": session_id,
    }
    text = render_markdown(metadata, body)
    created = _atomic_create(path, text)
    if not created:
        existing = read_document(path, "archive")
        if existing["metadata"].get("session_id") != session_id:
            raise StorageError(f"archive filename collision: {path}")
    return path, created
