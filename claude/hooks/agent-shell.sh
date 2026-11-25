#!/bin/bash
# SessionStart hook: give the agent's shell the plain commands.
#
# Claude Code's shell snapshot copies the aliases of ~/.zshrc, so in the Bash
# tool `ls` is eza, `rm` is trash, `find` is fd and `du` is the interactive
# ncdu. zsh also expands `=word` (`echo =====` stops the whole command) and
# stops a command whose glob matches nothing (`--include=*.ts`). The snapshot
# keeps aliases and functions, not shell options, so ~/.zshrc cannot fix this.
#
# Claude Code sources $CLAUDE_ENV_FILE before every Bash command. The lines
# written there undo the aliases and set the options for the agent only; the
# terminal keeps its aliases.

cat >/dev/null

[ -n "${CLAUDE_ENV_FILE-}" ] || exit 0

lines=(
  'unalias ls ll lt cat find rm top man diff du 2>/dev/null'
  'setopt no_equals no_nomatch'
)

for line in "${lines[@]}"; do
  grep -qxF -- "$line" "$CLAUDE_ENV_FILE" 2>/dev/null ||
    printf '%s\n' "$line" >>"$CLAUDE_ENV_FILE"
done

exit 0
