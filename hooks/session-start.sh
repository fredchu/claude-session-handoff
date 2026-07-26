#!/bin/bash
# Session Handoff — SessionStart hook
# Reads Markdown handoff shards from the handoff root and outputs to stdout.
# Claude Code injects this output as context at session start.
#
# Setup:
#   1. Edit AGENT_ID and HANDOFF_ROOT below
#   2. chmod +x this file
#   3. Add to .claude/settings.json under hooks.SessionStart

# ---- Configuration ----
AGENT_ID="Main"                        # Your agent name (e.g., "Pro CC", "Mini CC", "Main")
HANDOFF_ROOT="$HOME/.agents/handoff"   # Handoff store root (e.g., a folder in an Obsidian vault)
CLI="$HOME/.claude/skills/session-handoff/scripts/handoff_cli.py"
# -----------------------

if [ ! -f "$CLI" ]; then
  echo "ℹ️ handoff_cli.py not found ($CLI) — is the session-handoff skill installed?"
  exit 0
fi

# Prints the private shard ({root}/Active/{AGENT_ID}.md) plus every agent's
# shared shard ({root}/Shared/*.md), truncated to the char budgets. Shards not
# updated within --stale-days get a ⚠️ stale marker. Errors go to a log, never
# to stdout (stdout is injected as session context).
/usr/bin/python3 "$CLI" session-start \
  --root "$HANDOFF_ROOT" \
  --agent "$AGENT_ID" \
  --active-budget 1500 \
  --shared-budget 1000 \
  2>>"$HOME/.claude/scripts/handoff-fetch.log"
