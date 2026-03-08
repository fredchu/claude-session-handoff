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
# -----------------------

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
