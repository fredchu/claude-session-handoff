#!/bin/bash
# Session Handoff — SessionStart hook
# Reads handoff notes from Apple Notes and outputs to stdout.
# Claude Code injects this output as context at session start.
#
# Setup:
#   1. Edit AGENT_ID and NOTES_FOLDER below
#   2. chmod +x this file
#   3. Add to .claude/settings.json under hooks.SessionStart

# ---- Configuration ----
AGENT_ID="Main"           # Your agent name (e.g., "Pro CC", "Mini CC", "Main")
NOTES_FOLDER="Claude Workspace"  # Apple Notes folder where handoff notes live
DEDUP_SCRIPT="$HOME/.claude/skills/session-handoff/scripts/applescript_notes.py"  # for the dedup sweep
# -----------------------

# --- Self-healing dedup sweep (deterministic, runs every session start) ---
# Heals duplicate canonical handoff notes that any non-compliant write (ad-hoc
# AppleScript, MCP create-note, an agent without the fix) may have created —
# independent of whether the handoff skill ran. Prevention is LLM-compliance-
# dependent; this sweep is not. Output goes to a log, NEVER to stdout (stdout is
# injected as session context).
if [ -f "$DEDUP_SCRIPT" ]; then
  for _t in "Session Handoff — ${AGENT_ID}" "Session Handoff — Shared" "Session Handoff — Archive"; do
    _out=$(/usr/bin/python3 "$DEDUP_SCRIPT" --folder "$NOTES_FOLDER" dedup --title "$_t" --apply 2>&1)
    case "$_out" in
      "OK: "*) : ;;  # 0 or 1 note — nothing to heal
      *) printf '%s [%s] %s\n' "$(date '+%Y-%m-%dT%H:%M:%S')" "$_t" "$_out" >> "$HOME/.claude/scripts/handoff-dedup.log" ;;
    esac
  done
fi

read_note() {
  local title="$1"
  osascript -e "
    tell application \"Notes\"
      set matchingNotes to notes of folder \"$NOTES_FOLDER\" whose name is \"$title\"
      if (count of matchingNotes) > 0 then
        set noteBody to plaintext of item 1 of matchingNotes
        return noteBody
      else
        return \"\"
      end if
    end tell
  " 2>/dev/null
}

# Read private note
private_title="Session Handoff — ${AGENT_ID}"
private_content=$(read_note "$private_title")

# Read shared note
shared_content=$(read_note "Session Handoff — Shared")

# Output results
if [ -n "$private_content" ] || [ -n "$shared_content" ]; then
  if [ -n "$private_content" ]; then
    echo "${private_title} (updated: $(date)):"
    echo "$private_content"
  fi
  if [ -n "$shared_content" ]; then
    echo "Session Handoff — Shared (updated: $(date)):"
    echo "$shared_content"
  fi
else
  echo "ℹ️ No Session Handoff notes found."
fi
