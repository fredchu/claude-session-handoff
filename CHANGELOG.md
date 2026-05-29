## 1.4.0 - 2026-05-29

### Added
- Extracted all deterministic logic into stdlib-only Python scripts (`applescript_notes.py`, `consolidate_archive.py`, `count_archive_entries.py`, `lint_handoff_html.py`, `render_handoff_html.py`) with a pytest suite — replacing prose the executing LLM previously had to re-derive each run.
- Auto-triggered weekly consolidation after Phase 2: when the Archive reaches the threshold, consolidation now runs without asking.
- `applescript_notes.py dedup --title T [--apply]` — lists or heals duplicate exact-title notes, keeping the newest by a locale-independent `YYYYMMDDHHMMSS` sort key (id tie-break for same-second ties); deletes are idempotent under retry.
- **Deterministic SessionStart dedup sweep** in the example hook (`hooks/session-start.sh`): runs `dedup --apply` over all canonical titles every session start, logging to `~/.claude/scripts/handoff-dedup.log` and never to stdout. This is the real safety net — it heals duplicates regardless of how they were created, since write-path prevention is otherwise LLM-compliance-dependent.

### Fixed
- **Duplicate notes root cause.** Create/update was LLM-driven raw AppleScript with self-judged "first time vs update", producing duplicate canonical notes over time. All writes now go through an exact-title (`name is`, not `contains`) upsert in `applescript_notes.py write`, and `run_applescript` retries transient osascript failures (`-1719`/`-1712`/`-1700`/execution error/索引錯誤).
- Archive header regex now tolerates the `<br>` Apple Notes injects on round-trip (and self-closing `<br/>`), so `count_archive_entries.py` no longer reports 0 against a real Archive note.

### Changed
- **Writes no longer use raw AppleScript or MCP `create-note`** (supersedes the 1.3.0 note below). The workflow routes all create / update / archive-prepend through `applescript_notes.py write`, and adds a Phase 0 dedup precheck. An Apple Notes MCP is now optional and used only for reading/searching.

## 1.3.0 - 2026-04-27

### Changes
- Add macOS 26 HTML format rules table (h1/h2/h3 mapping, code block, list, blank line)
- Switch note creation from MCP `create-note` to AppleScript `make new note` (avoids title duplication)
- Switch note updates to prefer AppleScript `set body of` (MCP `update-note` allowed as fallback)
- Replace `<h2>` section headers with `<div><b>...</b></div>` to avoid font-size infection on older macOS

### Documentation
- Document macOS 26 HTML format requirements (Pro CC must follow)
- Note that h1/h2/h3 font-size infection was an OS bug fixed in current macOS

## 1.2.0 - 2026-03-25

### Features
- Expand Phase 4 from simple Spot Check to full Lesson Extraction system
- Add 5 detection signals: repeated edits, bash failure loops, user corrections, web search gaps, approach pivots
- Add 5-step extraction flow: scan → distill → route → ask user → cross-project promote
- Add lesson file format template for structured knowledge capture
- Add cross-project promote check (auto-suggest MEMORY.md promotion when 2+ projects share a lesson)

## 1.1.0 - 2026-03-08

### Features
- Read agent config (AgentID, notes folder, budget) from CLAUDE.md instead of hardcoding
- Add example SessionStart hook script (`hooks/session-start.sh`)
- Add macOS-only prerequisite notice

### Refactor
- Move SKILL.md to repo root for skills.sh compatibility

### Documentation
- Update installation to use `npx skills add`
- Add concrete hook setup steps and CLAUDE.md config examples

## 1.0.0 - 2026-03-08

### Features
- Multi-agent session handoff with private + shared Apple Notes
- Three-tier memory system: Active → Archive → Long-term
- Content routing with automatic deduplication
- Character budget enforcement (~2500 chars total)
- Weekly consolidation when archive reaches 5+ entries
- Spot check for real-time lesson detection
- Single-agent mode support
