# claude-session-handoff

A Claude Code skill that gives your AI persistent memory across sessions using Apple Notes.

**[繁體中文版 README](README.zh-TW.md)**

## The Problem

Claude Code sessions are stateless. Every time a session ends, all context vanishes. The next session starts from zero — no memory of what was done, what's in progress, or what decisions were made.

## The Solution

This skill writes structured handoff notes to Apple Notes before each session ends, and reads them back at the start of the next session via a `SessionStart` hook. It's like leaving yourself a sticky note, except the AI does it automatically.

## Architecture

```
Session ends
    ↓
┌─────────────────────────────────────────┐
│ [Private] Session Handoff — {AgentID}   │  ← per-agent working state
│ [Shared]  Session Handoff — Shared      │  ← cross-agent sync
└─────────────────────────────────────────┘
    ↓ old content archived
┌─────────────────────────────────────────┐
│ [Archive] Session Handoff — Archive     │  ← rolling history
└─────────────────────────────────────────┘
    ↓ weekly consolidation
┌─────────────────────────────────────────┐
│ [Long-term] MEMORY.md / memory files    │  ← distilled knowledge
└─────────────────────────────────────────┘
```

### Three-Tier Memory

| Tier | Storage | Lifecycle |
|------|---------|-----------|
| **Active** | Private + Shared notes | Overwritten each session |
| **Archive** | Archive note | Rolling, keeps last 5 entries |
| **Long-term** | MEMORY.md / memory files | Permanent, distilled patterns |

### Multi-Agent Support

If you run Claude Code on multiple machines (e.g., a laptop for interactive dev + a server for unattended tasks), each agent gets its own private note while sharing a common note for cross-agent coordination.

Single-agent mode is also supported — just skip the shared note.

## Installation

### 1. Install the skill

```bash
npx skills add fredchu/claude-session-handoff
```

### 2. Install Apple Notes MCP

You need an MCP server that can read/write Apple Notes. For example: [apple-notes-mcp](https://github.com/Dhravya/apple-notes-mcp)

```bash
claude mcp add --scope user apple-notes -- npx -y apple-notes-mcp
```

### 3. Configure SessionStart hook

Add a hook to `.claude/settings.json` that reads your handoff notes at session start:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "type": "command",
        "command": "your-script-to-read-handoff-notes.sh"
      }
    ]
  }
}
```

The script should search Apple Notes for your handoff notes and output their content to stdout.

### 4. Add trigger rules to CLAUDE.md

Add to your project or user `CLAUDE.md`:

```markdown
## Session Handoff
- When user says "bye", "done", "handoff", "收工", or "結束" → run `/session-handoff`
- Do NOT skip even if "nothing was done" this session
```

## Usage

Just say "bye" or "handoff" at the end of your session. The skill will:

1. **Archive** the previous handoff content
2. **Write** new private + shared notes
3. **Consolidate** weekly if archive has 5+ entries
4. **Spot check** for lessons worth saving to long-term memory

## How It Works

### Content Routing

```
This session's output
    ↓
Does another agent need to know?
    ├── Yes → Shared note
    └── No  → Private note
```

- **Private**: feature branches, environment-specific issues, this machine only
- **Shared**: cross-agent project state, user decisions, environment sync status

### Character Budget

Notes are kept compact to minimize token usage when injected at session start:

| Note | Budget |
|------|--------|
| Private | 1500 chars |
| Shared | 1000 chars |
| Total injected | ~2500 chars |

## Why Apple Notes?

- Native to macOS — no extra infra
- Syncs across devices via iCloud
- Full-text search
- Folders for organization
- MCP servers available

## License

MIT
