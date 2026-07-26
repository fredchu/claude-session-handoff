"""Shared utilities for session-handoff scripts."""

import re
import subprocess
import time
from html.parser import HTMLParser

FORBIDDEN_TAGS = ["<p>", "<p ", "</p>"]
FORBIDDEN_ATTRS_REGEX = r'font-size\s*:'
TRANSIENT_OSASCRIPT_ERRORS = ("-1719", "-1712", "-1700", "execution error", "索引錯誤")


def force_utf8_stdio() -> None:
    """Reconfigure stdout/stderr to UTF-8 (Windows pipes default to the ANSI codepage)."""
    import sys

    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts = []

    def handle_data(self, data):
        self._parts.append(data)

    def get_text(self):
        return "".join(self._parts)


def count_visible_chars(html: str) -> int:
    """Strip HTML tags and return count of visible characters."""
    extractor = _TextExtractor()
    extractor.feed(html)
    return len(extractor.get_text().strip())


def escape_applescript_str(s: str) -> str:
    """Escape string for use inside AppleScript double-quoted string literals."""
    s = s.replace("\\", "\\\\")
    s = s.replace('"', '\\"')
    return s


def _is_transient_osascript_error(stderr: str) -> bool:
    """Return True for intermittent osascript/Notes failures worth retrying."""
    normalized = stderr.lower()
    return any(marker.lower() in normalized for marker in TRANSIENT_OSASCRIPT_ERRORS)


def run_applescript(script: str, attempts=3, base_delay=0.3) -> str:
    """Run osascript -e <script> and return stdout stripped. Raises RuntimeError on failure."""
    total_attempts = max(1, int(attempts))
    last_stderr = ""

    for attempt_number in range(1, total_attempts + 1):
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return result.stdout.strip()

        last_stderr = result.stderr.strip()
        if not _is_transient_osascript_error(last_stderr):
            raise RuntimeError(f"osascript failed: {last_stderr}")
        if attempt_number < total_attempts:
            time.sleep(base_delay * attempt_number)

    raise RuntimeError(f"osascript failed: {last_stderr}")


# Header pattern for archive entries.
# Group 1: date (YYYY/MM/DD)
# Group 2: optional prefix token before [agent] (non-greedy, does not consume '[')
# Group 3: agent name inside [...]
# Group 4: summary text after "—"
# Apple Notes round-trip 會把粗體 header 切碎成多段 <b> 並在 CJK 括號外包
# <font face=".CJKSymbolsFallbackTC-Bold">（2026-07-08 實測），所以不能要求整個
# header 落在單一 <b> 內。改為逐 <div> 去 tag 後比對純文字。
_DIV_RE = re.compile(r'<div>(.*?)</div>', re.S)
_TAG_RE = re.compile(r'<[^>]+>')
_ENTRY_TEXT_RE = re.compile(
    r'^(\d{4}/\d{2}/\d{2})\s*(.*?)\s*\[\s*([^\]]+?)\s*\]\s*—\s*(.+)$'
)


def parse_archive_entries(archive_html: str) -> list:
    """
    Parse archive HTML into a list of entry dicts.

    Each entry starts with a header matching:
      <div><b>YYYY/MM/DD ... [AgentName] — summary text</b></div>

    Works regardless of whether entries are separated by newlines or not,
    by using finditer to locate header positions in the full string.

    Returns list of dicts with keys: date, agent, summary, raw.
    """
    header_matches = []
    for dm in _DIV_RE.finditer(archive_html):
        inner = dm.group(1)
        if '<b>' not in inner:
            continue  # header 一定帶粗體；避免誤認內文行
        text = _TAG_RE.sub('', inner).replace(' ', ' ').replace('\xa0', ' ').strip()
        tm = _ENTRY_TEXT_RE.match(text)
        if tm:
            header_matches.append((dm.start(), tm))
    if not header_matches:
        return []

    entries = []
    for i, (start, m) in enumerate(header_matches):
        end = header_matches[i + 1][0] if i + 1 < len(header_matches) else len(archive_html)
        raw = archive_html[start:end]
        entries.append({
            "date": m.group(1),
            "agent": m.group(3).strip(),
            "summary": m.group(4).strip(),
            "raw": raw,
        })

    return entries
