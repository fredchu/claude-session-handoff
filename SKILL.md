---
name: session-handoff
description: Save current session state to Apple Notes at session end. Triggers on "handoff", "bye", "done", "收工", "結束". Multi-agent architecture with private (per-agent) + shared (cross-agent) notes. Three-tier memory system: Active → Archive → Long-term.
---

# Session Handoff — Multi-Agent Three-Tier Memory System

## The Problem

Claude Code sessions are stateless. When a session ends, all context is lost. The next session starts from scratch — no memory of what was done, what's in progress, or what decisions were made.

This skill solves that by writing structured handoff notes to Apple Notes before each session ends, and reading them back at the start of the next session via a SessionStart hook.

## Architecture

```
Session ends
    ↓
[Private] Session Handoff — {AgentID}   ← read by this agent's hook
[Shared]  Session Handoff — Shared      ← read by all agents' hooks
    ↓ old content prepended to
[Mid-term] Session Handoff — Archive    ← merged history, tagged by agent
    ↓ periodic consolidation
[Long-term] Memory files (MEMORY.md)    ← distilled universal knowledge
```

### Agent Identification

Define your agents in CLAUDE.md. Example:

| AgentID | Machine | Role |
|---------|---------|------|
| `Main` | Primary dev machine | Interactive development |
| `Server` | Always-on server | Unattended tasks, cron jobs |

To add a new agent, just add a row. Note naming extends automatically.

## Note Naming

| Note | Title | Written by | Read by |
|------|-------|------------|---------|
| Private | `Session Handoff — {AgentID}` | Self | Self |
| Shared | `Session Handoff — Shared` | Any agent | All agents |
| Archive | `Session Handoff — Archive` | Any agent | On demand |

## Content Routing (Key to Deduplication)

```
This session's output
    ↓
Does another agent need to know?
    ├── Yes → Write to Shared
    └── No  → Write to Private
```

| Where | Content type | Example |
|-------|-------------|---------|
| **Private** | Work only this agent is doing | A feature branch in progress |
| **Private** | Environment-specific issues | PATH problems on this machine |
| **Shared** | Cross-agent project state | App developed on Main, deploying to Server |
| **Shared** | User decisions/preference changes | User decided to deprecate a tool |
| **Shared** | One side done, other needs to know | Main installed a new MCP, Server needs it too |

**Dedup rule: Content written to Shared is NOT repeated in Private.**

## Character Budget

| Note | Budget |
|------|--------|
| Private | 1500 chars |
| Shared | 1000 chars |
| Hook-injected context total | ~2500 chars |

## Workflow

### Phase 1: Archive (Preserve Old Content)

1. Search for own private note `Session Handoff — {AgentID}`
2. If found, read its content
3. Search for `Session Handoff — Archive`
   - Exists → prepend old private content to Archive top (with date separator, tagged with AgentID)
   - Not found → create Archive, move to designated Apple Notes folder
4. Search for `Session Handoff — Shared`, read existing shared content (Phase 2 determines what to update)

### Phase 2: Write (Overwrite Private + Update Shared)

1. Review this session's conversation, route content:
   - Only relevant to self → write to Private
   - Useful across agents → write to Shared
2. Overwrite private note `Session Handoff — {AgentID}`
   - First time: `create-note` + `move-note` to designated folder
3. Update Shared note (only update own sections, never delete other agents' content)
   - First time: `create-note` + `move-note` to designated folder
4. Use `<h2>` to separate multiple projects

### Phase 3: Weekly Consolidation (Triggered when Archive >= 5 entries)

1. **Generate weekly report** → save to memory/episodic directory
2. **Distill patterns** → scan Archive for recurring cross-agent issues
3. **Clean Archive** → keep only the most recent 5 entries

### Phase 4: Spot Check (Real-time Detection)

When a clear lesson is learned during the session, suggest writing it to long-term memory.

## Private Note Format

```html
<h1>Session Handoff — Main</h1>
<p><i>Updated: 2026/03/08</i></p>

<h2>Project Alpha</h2>
<h3>Continuing work</h3>
<ul><li>NLP pipeline optimization</li></ul>
<h3>Completed this session</h3>
<ul><li>Refactored data fetcher</li></ul>
```

## Shared Note Format

```html
<h1>Session Handoff — Shared</h1>
<p><i>Last updated: 2026/03/08 by Main</i></p>

<h2>Environment Sync</h2>
<ul>
<li>New MCP server installed globally — Main done, Server pending</li>
</ul>

<h2>Cross-Agent Project State</h2>
<ul>
<li>Project Alpha: developed on Main, ready to deploy to Server</li>
</ul>

<h2>User Decisions</h2>
<ul>
<li>Deprecated tool X, using tool Y going forward</li>
</ul>
```

## Archive Entry Format

Each entry tagged with source agent:

```html
<h3>2026/03/08 [Main] — Project Alpha, Assistant System</h3>
<p>[compressed handoff content]</p>
<hr>
<h3>2026/03/08 [Server] — Deploy Pipeline</h3>
<p>[compressed handoff content]</p>
<hr>
```

## Rules

- NEVER skip handoff with "nothing was done" — even a briefing session gets a note
- Confirm to user after writing handoff
- Private note title is always `Session Handoff — {AgentID}`
- Shared note title is always `Session Handoff — Shared`
- When updating Shared, only update own sections — never delete other agents' content
- Multiple projects in one note, separated by `<h2>`

## Prerequisites

- **Apple Notes MCP** — for reading/writing notes (e.g., [apple-notes-mcp](https://github.com/Dhravya/apple-notesapple-notes-mcp))
- **SessionStart hook** — to inject handoff content at session start (configure in `.claude/settings.json`)

### Example SessionStart Hook

Add to your `.claude/settings.json`:

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

The hook script should search Apple Notes for `Session Handoff — {AgentID}` and `Session Handoff — Shared`, then output their content to stdout. Claude Code will inject this as context at session start.

## Single-Agent Mode

If you only have one Claude Code instance, you can simplify:

- Skip the Shared note entirely
- Use a single `Session Handoff` note (no AgentID suffix)
- Archive and consolidation work the same way
- Character budget: ~2000 chars for the single note
