# Shell Environment Reference

Source: `~/Developer/dotfiles/shell/.zshrc` (symlinked to `~/.zshrc`)

Claude Code's Bash tool loads a snapshot of this shell, aliases included. The SessionStart hook `claude/hooks/agent-shell.sh` undoes the aliases that stand in for a standard command (`ls`, `ll`, `lt`, `cat`, `find`, `rm`, `top`, `man`, `diff`, `du`) and sets `no_equals` and `no_nomatch`, for the agent only. So in the Bash tool `ls`, `rm` and `find` are the system commands, `echo =====` prints, and an unmatched glob such as `--include=*.ts` reaches the command as written. The other aliases below are there too; the terminal keeps all of them.

## Exit status

A command's exit status is read right after it runs, before any pipe or substitution: `cmd >"$out" 2>&1; rc=$?`, then read `$out`. `cmd | tail` reports `tail`'s status, and `$?` read after a `$(…)` reports the substitution's. With a pipe, zsh keeps each status in `$pipestatus[1]`…, bash in `${PIPESTATUS[0]}`….

## Aliases

### CLI Replacements
| Alias | Expands to |
|---|---|
| `ls` | `eza --icons --group-directories-first` |
| `ll` | `eza --icons --group-directories-first -la` |
| `lt` | `eza --icons --tree --level=2` |
| `cat` | `bat --paging=never` |
| `find` | `fd` |
| `rm` | `trash` (moves to Trash) |
| `top` | `htop` |
| `man` | `tldr` |
| `diff` | `delta` |
| `lg` | `lazygit` |
| `du` | `ncdu` |

### Yarn / npm
| Alias | Expands to |
|---|---|
| `nr` | `yarn` |
| `nrd` | `yarn dev` |
| `nrs` | `yarn start` |
| `nrt` | `yarn test` |
| `nrb` | `yarn build` |
| `nrl` | `yarn lint` |
| `nrlf` | `yarn lint:fix` |
| `nrv` | `yarn validate` |

### React Native
| Alias | Expands to |
|---|---|
| `pod` | `cd ios && pod install && cd ..` |
| `podclean` | `cd ios && pod deintegrate && pod install && cd ..` |
| `rni` | `yarn ios` |
| `rna` | `yarn android` |
| `rns` | `yarn start` |
| `rnsr` | `yarn start:reset` |

### Navigation
| Alias | Expands to |
|---|---|
| `dev` | `cd ~/Developer` |
| `dots` | `cd ~/Developer/dotfiles` |

### System
| Alias | Expands to |
|---|---|
| `flush` | Flush DNS cache |
| `ip` | Public IP address |
| `localip` | Local IP address |

### Docker (Colima)
| Alias | Expands to |
|---|---|
| `dcu` | `docker compose up -d` |
| `dcd` | `docker compose down` |
| `dcl` | `docker compose logs -f` |

### Git
| Alias | Expands to |
|---|---|
| `gp` | `git push` |
| `gpl` | `git pull` |
| `gcm` | `git checkout main` |

### Shell
| Alias | Expands to |
|---|---|
| `reload` | `source ~/.zshrc` |

## Functions

- `mkcd <name>` — create a directory and cd into it
- `killport <port>` — kill whatever is running on that port
- `aliases` — print the full alias help table

## Shell Features

- **Auto nvm use**: switches Node version on cd when `.nvmrc` is present
- **Auto-ls**: shows directory contents after every cd (via eza)
- **History**: 50k entries, deduplicated, shared across terminal tabs
- **zoxide**: `z` for smart cd (remembers frequently visited directories)
- **fzf**: Ctrl+R for fuzzy history search, Ctrl+T for file search

## Git Aliases (.gitconfig)

| Alias | Expands to |
|---|---|
| `git co` | `checkout` |
| `git br` | `branch` |
| `git st` | `status -sb` |
| `git ci` | `commit` |
| `git ca` | `commit --amend` |
| `git cp` | `cherry-pick` |
| `git df` | `diff` |
| `git ds` | `diff --staged` |
| `git lg` | `log --oneline --graph -20` |
| `git la` | `log --oneline --all -30` |
| `git last` | `log -1 --stat` |
| `git undo` | `reset --soft HEAD~1` |
| `git unstage` | `reset HEAD --` |
| `git wip` | `stash push -m "WIP"` |
| `git pop` | `stash pop` |
| `git branches` | `branch -a` (sorted by date) |
| `git tags` | `tag -l` (sorted by version) |
| `git amend` | `commit --amend --no-edit` |
| `git fixup` | `commit --fixup` |
| `git prune-merged` | Delete local branches merged into main |

Run `git aliases` in the terminal for a formatted table.
