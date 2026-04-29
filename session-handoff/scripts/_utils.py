"""Shared utilities for session-handoff scripts."""

import re
import subprocess
from html.parser import HTMLParser

FORBIDDEN_TAGS = ["<p>", "<p ", "</p>"]
FORBIDDEN_ATTRS_REGEX = r'font-size\s*:'


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


def run_applescript(script: str) -> str:
    """Run osascript -e <script> and return stdout stripped. Raises RuntimeError on failure."""
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"osascript failed: {result.stderr.strip()}")
    return result.stdout.strip()


# Header pattern for archive entries.
# Group 1: date (YYYY/MM/DD)
# Group 2: optional prefix token before [agent] (non-greedy, does not consume '[')
# Group 3: agent name inside [...]
# Group 4: summary text after "—"
_ENTRY_HEADER_RE = re.compile(
    r'<div><b>(\d{4}/\d{2}/\d{2})\s*([^\[]*?)\s*\[([^\]]+)\]\s*—\s*([^<]+)</b></div>'
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
    header_matches = list(_ENTRY_HEADER_RE.finditer(archive_html))
    if not header_matches:
        return []

    entries = []
    for i, m in enumerate(header_matches):
        start = m.start()
        end = header_matches[i + 1].start() if i + 1 < len(header_matches) else len(archive_html)
        raw = archive_html[start:end]
        entries.append({
            "date": m.group(1),
            "agent": m.group(3).strip(),
            "summary": m.group(4).strip(),
            "raw": raw,
        })

    return entries
