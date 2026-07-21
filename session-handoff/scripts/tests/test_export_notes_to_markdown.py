import copy

import pytest

from export_notes_to_markdown import (
    DEFAULT_ACTIVE_TITLE,
    DEFAULT_ARCHIVE_TITLE,
    DEFAULT_SHARED_TITLE,
    export_notes,
)
from markdown_storage import StorageError, read_shard, scan_archive_entries


def note_sources():
    return {
        DEFAULT_ACTIVE_TITLE: "<div>Active title</div><ul><li>current work</li></ul>",
        DEFAULT_SHARED_TITLE: "<div>Shared title</div><div>tell Mini CC</div>",
        DEFAULT_ARCHIVE_TITLE: (
            "<div>Session Handoff — Archive</div>"
            "<div><b>2026/07/16 [Pro CC] — previous work</b></div>"
            "<div>archive detail</div>"
        ),
    }


def test_exporter_reads_notes_and_only_writes_markdown(tmp_path):
    notes = note_sources()
    original = copy.deepcopy(notes)
    reads = []

    def reader(title):
        reads.append(title)
        return notes[title]

    paths = export_notes(
        tmp_path, "Pro CC", "2026-07-17T10:00:00+08:00", reader
    )
    assert reads == [DEFAULT_ACTIVE_TITLE, DEFAULT_SHARED_TITLE, DEFAULT_ARCHIVE_TITLE]
    assert notes == original
    assert len(paths) == 3
    assert "current work" in read_shard(tmp_path, "active", "Pro CC")["body"]
    assert "tell Mini CC" in read_shard(tmp_path, "shared", "Pro CC")["body"]
    assert "archive detail" in scan_archive_entries(tmp_path)[0]["body"]


def test_exporter_archive_rerun_does_not_duplicate_session(tmp_path):
    notes = note_sources()
    reader = notes.__getitem__
    export_notes(tmp_path, "Pro CC", "2026-07-17T10:00:00+08:00", reader)
    export_notes(tmp_path, "Pro CC", "2026-07-17T11:00:00+08:00", reader)
    assert len(scan_archive_entries(tmp_path)) == 1


def test_unparseable_nonempty_archive_writes_nothing(tmp_path):
    notes = note_sources()
    notes[DEFAULT_ARCHIVE_TITLE] = (
        "<div><b>2026/07/16 [Pro CC] - broken separator</b></div><div>important</div>"
    )
    with pytest.raises(StorageError, match="Archive parse mismatch"):
        export_notes(tmp_path, "Pro CC", "2026-07-17T10:00:00+08:00", notes.__getitem__)
    assert not tmp_path.joinpath("Active").exists()
    assert not tmp_path.joinpath("Shared").exists()
    assert not tmp_path.joinpath("Archive").exists()


def test_one_corrupt_archive_entry_prevents_partial_export(tmp_path):
    notes = note_sources()
    notes[DEFAULT_ARCHIVE_TITLE] += (
        "<div><b>2026/07/15 [Mini CC] - broken separator</b></div><div>must not drop</div>"
    )
    with pytest.raises(StorageError, match="found 2 dated headers but parsed 1"):
        export_notes(tmp_path, "Pro CC", "2026-07-17T10:00:00+08:00", notes.__getitem__)
    assert list(tmp_path.rglob("*.md")) == []
