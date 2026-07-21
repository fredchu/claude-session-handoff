import datetime as dt
from concurrent.futures import ThreadPoolExecutor

import pytest

from markdown_storage import (
    compose_session_start,
    SchemaError,
    StorageError,
    read_document,
    read_shard,
    scan_archive_entries,
    shard_path,
    write_archive_entry,
    write_shard,
)

UPDATED = "2026-07-17T10:00:00+08:00"


def test_agents_only_overwrite_their_own_shards(tmp_path):
    pro = write_shard(tmp_path, "active", "Pro CC", "Pro CC", "pro", UPDATED)
    mini = write_shard(tmp_path, "active", "Mini CC", "Mini CC", "mini", UPDATED)
    with pytest.raises(StorageError, match="cannot overwrite"):
        write_shard(tmp_path, "active", "Mini CC", "Pro CC", "wrong", UPDATED)
    assert read_document(pro, "active")["body"].strip() == "pro"
    assert read_document(mini, "active")["body"].strip() == "mini"


def test_stale_shard_is_marked_with_source_timestamp(tmp_path):
    write_shard(tmp_path, "shared", "Pro CC", "Pro CC", "handoff", UPDATED)
    now = dt.datetime(2026, 7, 17, 20, 0, tzinfo=dt.timezone(dt.timedelta(hours=8)))
    result = read_shard(tmp_path, "shared", "Pro CC", dt.timedelta(hours=4), now)
    assert result["stale"] is True
    assert result["metadata"]["updated_at"] == UPDATED


def test_two_agents_writing_concurrently_have_no_lost_update(tmp_path):
    def write(agent):
        write_shard(tmp_path, "active", agent, agent, f"active {agent}", UPDATED)
        write_shard(tmp_path, "shared", agent, agent, f"shared {agent}", UPDATED)

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(write, ["Pro CC", "Mini CC"]))

    for agent in ("Pro CC", "Mini CC"):
        assert read_shard(tmp_path, "active", agent)["body"].strip() == f"active {agent}"
        assert read_shard(tmp_path, "shared", agent)["body"].strip() == f"shared {agent}"


def test_session_start_composes_own_active_and_all_shared_with_total_budget(tmp_path):
    write_shard(tmp_path, "active", "Pro CC", "Pro CC", "private", UPDATED)
    write_shard(tmp_path, "active", "Mini CC", "Mini CC", "do not inject", UPDATED)
    write_shard(tmp_path, "shared", "Pro CC", "Pro CC", "P" * 800, UPDATED)
    write_shard(tmp_path, "shared", "Mini CC", "Mini CC", "M" * 800, UPDATED)

    result = compose_session_start(tmp_path, "Pro CC", shared_budget=1000)
    assert result["active"]["body"].strip() == "private"
    assert {item["metadata"]["agent"] for item in result["shared"]} == {"Pro CC", "Mini CC"}
    assert sum(len(item["body"]) for item in result["shared"]) == 1000
    assert result["shared_truncated"] is True


def test_archive_rerun_is_idempotent_for_same_session(tmp_path):
    first, created = write_archive_entry(
        tmp_path, "Pro CC", "session-123", "work", "first", UPDATED
    )
    second, created_again = write_archive_entry(
        tmp_path, "Pro CC", "session-123", "renamed", "changed", "2026-07-17T11:00:00+08:00"
    )
    assert created is True
    assert created_again is False
    assert second == first
    assert len(scan_archive_entries(tmp_path)) == 1
    assert read_document(first, "archive")["body"].strip() == "first"


def test_archive_entry_cannot_be_overwritten(tmp_path):
    path, _ = write_archive_entry(tmp_path, "Pro CC", "one", "same", "first", UPDATED)
    with pytest.raises(StorageError, match="filename collision"):
        write_archive_entry(tmp_path, "Pro CC", "two", "same", "second", UPDATED)
    assert read_document(path, "archive")["body"].strip() == "first"


def test_safe_path_rejects_traversal(tmp_path):
    with pytest.raises(StorageError, match="unsafe agent"):
        shard_path(tmp_path, "active", "../other")


def test_corrupt_document_read_fails_closed(tmp_path):
    path = tmp_path / "bad.md"
    path.write_text("---\nkind: active\n---\nimportant", encoding="utf-8")
    with pytest.raises(SchemaError, match="missing frontmatter fields"):
        read_document(path)
    assert path.read_text(encoding="utf-8").endswith("important")
