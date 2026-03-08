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
