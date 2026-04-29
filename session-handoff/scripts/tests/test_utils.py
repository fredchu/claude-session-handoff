import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from _utils import count_visible_chars, escape_applescript_str, parse_archive_entries


def test_count_visible_chars_basic():
    assert count_visible_chars("<div><b>Hello</b></div>") == 5


def test_count_visible_chars_empty():
    assert count_visible_chars("<div><br></div>") == 0


def test_count_visible_chars_whitespace_stripped():
    # Leading/trailing whitespace inside tags should be stripped
    assert count_visible_chars("<div>  Hi  </div>") == 2


def test_escape_applescript_str_plain():
    assert escape_applescript_str("hello world") == "hello world"


def test_escape_applescript_str_quotes():
    # Double-quotes should be backslash-escaped
    result = escape_applescript_str('say "hello"')
    assert '\\"' in result
    assert "hello" in result


def test_escape_applescript_str_backslash():
    # Backslashes escaped first
    result = escape_applescript_str("a\\b")
    assert result == "a\\\\b"


def test_parse_archive_entries_basic():
    html = (
        "<div><b>2026/04/29 Pro [Pro CC] — MEMORY.md 瘦身</b></div>"
        "<div>details</div>"
    )
    entries = parse_archive_entries(html)
    assert len(entries) == 1
    assert entries[0]["date"] == "2026/04/29"
    assert entries[0]["agent"] == "Pro CC"
    assert "MEMORY.md 瘦身" in entries[0]["summary"]


def test_parse_archive_entries_empty():
    entries = parse_archive_entries("<div>no headers here</div>")
    assert entries == []


def test_parse_archive_entries_multiple():
    html = (
        "<div><b>2026/04/28 A1 [Mini CC] — task A</b></div><div>a</div>\n"
        "<div><b>2026/04/29 A2 [Pro CC] — task B</b></div><div>b</div>\n"
    )
    entries = parse_archive_entries(html)
    assert len(entries) == 2
    assert entries[0]["date"] == "2026/04/28"
    assert entries[1]["date"] == "2026/04/29"
