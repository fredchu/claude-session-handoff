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
