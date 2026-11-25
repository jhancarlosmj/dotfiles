#!/usr/bin/env bash
# Feeds the status line JSON to Orca's rate-limit hook (when inside an Orca
# pane) and renders the visible line with statusline.sh.
input="$(cat)"

orca_hook="$HOME/.orca/agent-hooks/claude-statusline.sh"
if [ -n "${ORCA_PANE_KEY-}${ORCA_AGENT_PANE-}" ] && [ -x "$orca_hook" ]; then
  printf '%s' "$input" | /bin/sh "$orca_hook" >/dev/null 2>&1 &
fi

printf '%s' "$input" | bash "$HOME/.claude/statusline.sh"
