# claude-session-handoff

A Claude Code skill that gives your AI persistent memory across sessions using plain Markdown files — Obsidian-vault friendly.

> Requires Python 3 (stdlib only). Any writable directory works as the store; an iCloud-synced Obsidian vault is what the author uses. Legacy Apple Notes migration tools (macOS only) are included.

**[繁體中文版 README](README.zh-TW.md)**

## The Problem

Claude Code sessions are stateless. Every time a session ends, all context vanishes. The next session starts from zero — no memory of what was done, what's in progress, or what decisions were made.

## The Solution

This skill writes structured Markdown handoff shards to a filesystem store before each session ends, and reads them back at the start of the next session via a `SessionStart` hook. It's like leaving yourself a sticky note, except the AI does it automatically.

> **v2.0 storage cutover** — the backend switched from Apple Notes to plain Markdown files. If you used v1.x, see [Migrating from Apple Notes](#migrating-from-apple-notes-v1x).

## Architecture

```
Session ends
    ↓
┌───────────────────────────────────────────────┐
│ [Private] {root}/Active/{AgentID}.md          │  ← per-agent working state
│ [Shared]  {root}/Shared/{AgentID}.md          │  ← cross-agent sync (per-agent shard)
└───────────────────────────────────────────────┘
    ↓ old content archived
┌───────────────────────────────────────────────┐
│ [Archive] {root}/Archive/{YYYY}/….md          │  ← one file per session
└───────────────────────────────────────────────┘
    ↓ periodic consolidation
┌───────────────────────────────────────────────┐
│ [Long-term] MEMORY.md / episodic memory files │  ← distilled knowledge
└───────────────────────────────────────────────┘
```

Every file carries YAML frontmatter (`schema_version / kind / agent / updated_at`), generated and validated by the bundled scripts. Malformed files fail loudly instead of being silently mangled.

### Three-Tier Memory

| Tier | Storage | Lifecycle |
|------|---------|-----------|
| **Active** | Private + Shared shards | Overwritten each session |
| **Archive** | `Archive/{YYYY}/` files | Rolling, keeps last 5 entries |
| **Long-term** | MEMORY.md / episodic files | Permanent, distilled patterns |

### Multi-Agent Support

If you run Claude Code on multiple machines (e.g., a laptop for interactive dev + a server for unattended tasks), each agent writes its own private shard **and its own shared shard** (`Shared/{AgentID}.md`) — no agent ever touches another agent's files. At session start, each agent's hook merges every `Shared/*.md`.

Single-agent mode is also supported — just skip the shared shard.

## Installation

### 1. Install the skill

```bash
npx skills add fredchu/claude-session-handoff
```

### 2. Pick a handoff root

Any writable directory. Two common choices:

- `~/.agents/handoff` — local only, zero dependencies
- A folder inside an Obsidian vault on iCloud/Syncthing — synced across machines, browsable in Obsidian

```bash
mkdir -p ~/.agents/handoff
```

### 3. Configure the SessionStart hook

Copy the example hook and set your agent name and root:

```bash
cp hooks/session-start.sh ~/.claude/hooks/session-start.sh
chmod +x ~/.claude/hooks/session-start.sh
# Edit AGENT_ID and HANDOFF_ROOT in the script
```

Add to `.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "type": "command",
        "command": "~/.claude/hooks/session-start.sh"
      }
    ]
  }
}
```

The hook calls `handoff_cli.py session-start`, which prints the private shard plus every agent's shared shard (with a `⚠️ stale` marker on shards older than `--stale-days`, default 14).

### 4. Add config and trigger rules to CLAUDE.md

Add to your user-level `CLAUDE.md` (`~/.claude/CLAUDE.md`):

```markdown
## Session Handoff Config
- Agent ID: Main
- Handoff root: ~/.agents/handoff
- Other Agents: (leave empty for single-agent mode)
- Private budget: 1500 chars
- Shared budget: 1000 chars

## Session Handoff Rules
- When user says "bye", "done", "handoff", "收工", or "結束" → run `/session-handoff`
- Do NOT skip even if "nothing was done" this session
```

## Usage

Just say "bye" or "handoff" at the end of your session. The skill will:

1. **Archive** the previous handoff content (one frontmatter-tagged file per session)
2. **Write** new private + shared shards via `handoff_cli.py`
3. **Consolidate** automatically when the Archive reaches 5+ entries (old entries distilled into episodic memory)
4. **Extract lessons** worth saving to long-term memory

## How It Works

### All writes go through one CLI

The executing LLM never writes shard files by hand. Every write (Active / Shared / Archive) goes through `scripts/handoff_cli.py`, which handles frontmatter generation, schema validation, atomic writes, and path-escape protection:

```bash
python3 scripts/handoff_cli.py write   --root "$ROOT" --kind active --agent "Main" --body-file /tmp/private.md
python3 scripts/handoff_cli.py write   --root "$ROOT" --kind shared --agent "Main" --body-file /tmp/shared.md
python3 scripts/handoff_cli.py archive --root "$ROOT" --agent "Main" --session-id "20260726-topic" --slug "topic" --body-file /tmp/old.md
```

Reads are just file reads. This design came from hard experience: letting the LLM improvise storage writes (the v1.x Apple Notes era) produced duplicate notes and mangled content; deterministic scripts fixed it at the source. Atomic writes also keep cloud sync from uploading half-written files.

### Content Routing

```
This session's output
    ↓
Does another agent need to know?
    ├── Yes → Shared shard
    └── No  → Private shard
```

- **Private**: feature branches, environment-specific issues, this machine only
- **Shared**: cross-agent project state, user decisions, environment sync status

### Character Budget

Shards are kept compact to minimize token usage when injected at session start:

| Shard | Budget |
|------|--------|
| Private | 1500 chars |
| Shared | 1000 chars |
| Total injected | ~2500 chars |

## Why plain Markdown?

- Git-diffable, greppable, no vendor lock-in
- Works with any sync layer (iCloud, Syncthing, git) and browsable in Obsidian
- Schema-validated frontmatter — corruption fails loudly
- No AppleScript flakiness, no HTML round-trip mangling (Apple Notes used to shred CJK bold headers into fragments)
- Cross-platform: the storage scripts are stdlib-only Python

## Migrating from Apple Notes (v1.x)

The repo keeps the legacy tooling for a one-time export:

```bash
python3 scripts/export_notes_to_markdown.py --root ~/.agents/handoff --agent "Main" \
  --folder "Claude Workspace"
```

This converts your existing Private / Shared / Archive notes into the Markdown store. After exporting, stop writing to Apple Notes entirely — the old notes become a frozen archive.

## License

MIT
