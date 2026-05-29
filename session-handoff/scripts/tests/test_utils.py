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


def test_parse_archive_entries_apple_notes_roundtrip_format():
    # Apple Notes injects <br> before </div> in headers and uses grey <font>
    # <br> dividers between entries — verbatim sample from a real Archive note.
    html = (
        "<div><b>2026/05/15 [Pro CC] — book-translator OSS extract</b><br></div>"
        "<div>detail line one</div>"
        "<div><font color=\"#808080\"><br></font></div>"
        "<div><b>2026/05/14 [Pro CC] — FT Sheets auth: OAuth → SA</b><br></div>"
        "<div>detail line two</div>"
        "<div><font color=\"#808080\"><br></font></div>"
        "<div><b>2026/05/13 [Pro CC] — session-handoff comparison</b><br></div>"
        "<div>detail line three</div>"
    )
    entries = parse_archive_entries(html)
    assert len(entries) == 3
    assert entries[0]["date"] == "2026/05/15"
    assert entries[0]["agent"] == "Pro CC"
    assert "book-translator OSS extract" in entries[0]["summary"]
    assert entries[2]["date"] == "2026/05/13"


def test_parse_archive_entries_br_self_closing():
    # Some renderers emit <br/> instead of <br>; both must work.
    html = "<div><b>2026/05/01 [Pro CC] — task</b><br/></div><div>body</div>"
    entries = parse_archive_entries(html)
    assert len(entries) == 1
    assert entries[0]["date"] == "2026/05/01"
