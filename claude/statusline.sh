#!/usr/bin/env bash
set -u
INPUT="$(cat)"
export INPUT_JSON="$INPUT"

# Terminal width for flex-spacer math. Honors STATUSLINE_COLS env override
# (used by parity tests); otherwise tries tput, finally falls back to 80.
STATUSLINE_COLS=${STATUSLINE_COLS:-$(tput cols 2>/dev/null || echo 80)}

# Visible-character length: strip CSI SGR sequences then count chars.
# Wide glyphs (emoji, CJK) count as 1 column — same simplification as the
# interpret backend uses.
__visible_len() {
  printf '%s' "$1" | sed 's/\x1b\[[0-9;]*m//g' | awk '{ printf "%s", length($0) }'
}

__repeat_char() {
  local ch="$1" n="$2" out=""
  if [ "$n" -le 0 ]; then printf ''; return; fi
  local i=0
  while [ "$i" -lt "$n" ]; do out+="$ch"; i=$((i+1)); done
  printf '%s' "$out"
}

__sgr() { printf '\033[%sm' "$1"; }
__reset() { printf '\033[0m'; }

if command -v jq >/dev/null 2>&1; then
  __field() {
    printf '%s' "$INPUT_JSON" | jq -r --arg p "$1" '
      ($p | split(".")) as $parts
      | reduce $parts[] as $k (.; if type == "object" and has($k) then .[$k] else null end)
      | if . == null then "" else (if type == "string" then . else tostring end) end
    ' 2>/dev/null
  }
else
  if command -v python3 >/dev/null 2>&1 && python3 -c 'import sys' >/dev/null 2>&1; then
    __PY=python3
  elif command -v python >/dev/null 2>&1; then
    __PY=python
  else
    __PY=""
  fi
  __field() {
    if [ -z "$__PY" ]; then printf ''; return; fi
    PATH_ARG="$1" "$__PY" - <<'PYEOF' 2>/dev/null
import json, os
d = json.loads(os.environ.get('INPUT_JSON','{}') or '{}')
p = os.environ.get('PATH_ARG','')
cur = d
for part in p.split('.'):
    if isinstance(cur, dict) and part in cur:
        cur = cur[part]
    else:
        cur = None
        break
if cur is None:
    print('', end='')
elif isinstance(cur, bool):
    print('true' if cur else 'false', end='')
else:
    print(cur, end='')
PYEOF
  }
fi

__basename() { local s="$1"; printf '%s' "${s##*/}"; }
__compact() {
  local s="$1"
  if [ -z "$s" ]; then printf ''; return; fi
  # Use awk so we don't depend on bash arrays. Split on '/', take the first
  # char of every segment except the last; preserve a leading slash by
  # emitting an empty initial element when the path starts with '/'.
  printf '%s' "$s" | awk 'BEGIN{FS="/"} {
    out=""
    for (i=1; i<=NF; i++) {
      if (i==NF) { piece = $i }
      else if ($i == "") { piece = "" }
      else { piece = substr($i, 1, 1) }
      if (i==1) { out = piece } else { out = out "/" piece }
    }
    printf "%s", out
  }'
}
__tildify() {
  local s="$1"
  local home="${HOME%/}"
  if [ -n "$home" ] && [[ "$s" == "$home"* ]]; then
    printf '~%s' "${s#$home}"
    return
  fi
  if [[ "$s" =~ ^/(Users|home)/[^/]+(.*)$ ]]; then
    printf '~%s' "${BASH_REMATCH[2]}"
    return
  fi
  printf '%s' "$s"
}
__truncate() {
  local s="$1" n="$2"
  if [ "$n" -le 0 ] || [ "${#s}" -le "$n" ]; then printf '%s' "$s"; return; fi
  if [ "$n" -le 1 ]; then printf '%s' "${s:0:$n}"; return; fi
  printf '%s…' "${s:0:$((n-1))}"
}
__cost_fmt() { printf '$%.*f' "$2" "$1"; }
__dur_hms() {
  local ms="$1" total h m s
  total=$((ms/1000)); h=$((total/3600)); m=$(((total%3600)/60)); s=$((total%60))
  if [ "$h" -gt 0 ]; then printf '%d:%02d:%02d' "$h" "$m" "$s"
  else printf '%d:%02d' "$m" "$s"; fi
}
__dur_human() {
  local ms="$1" total m s h mm
  total=$((ms/1000))
  if [ "$total" -lt 60 ]; then printf '%ds' "$total"; return; fi
  m=$((total/60)); s=$((total%60))
  if [ "$m" -lt 60 ]; then
    if [ "$s" -gt 0 ]; then printf '%dm %ds' "$m" "$s"; else printf '%dm' "$m"; fi
    return
  fi
  h=$((m/60)); mm=$((m%60))
  if [ "$mm" -gt 0 ]; then printf '%dh %dm' "$h" "$mm"; else printf '%dh' "$h"; fi
}
__bar() {
  local pct="$1" width="$2" filled="$3" empty="$4"
  local p i n=0 e=0
  p=${pct%.*}
  [ -z "$p" ] && p=0
  if [ "$p" -lt 0 ]; then p=0; fi
  if [ "$p" -gt 100 ]; then p=100; fi
  n=$(( (p * width + 50) / 100 ))
  e=$((width - n))
  local out=""
  for ((i=0; i<n; i++)); do out+="$filled"; done
  for ((i=0; i<e; i++)); do out+="$empty"; done
  printf '%s' "$out"
}
__git_branch() {
  local cwd dir
  cwd="$(__field workspace.current_dir)"
  if [ -z "$cwd" ]; then cwd="$(__field cwd)"; fi
  if [ -n "$cwd" ] && command -v git >/dev/null 2>&1; then
    git -C "$cwd" rev-parse --abbrev-ref HEAD 2>/dev/null
  else
    __field workspace.git_worktree
  fi
}
__git_dirty() {
  local cwd
  cwd="$(__field workspace.current_dir)"
  if [ -z "$cwd" ]; then cwd="$(__field cwd)"; fi
  if [ -n "$cwd" ] && command -v git >/dev/null 2>&1; then
    if [ -n "$(git -C "$cwd" status --porcelain 2>/dev/null)" ]; then printf '1'; else printf '0'; fi
  else
    printf '0'
  fi
}
__emit() {
  local style="$1" text="$2"
  if [ -n "$style" ]; then __sgr "$style"; fi
  printf '%s' "$text"
  if [ -n "$style" ]; then __reset; fi
}
__norm_int() {
  # Coerce a possibly-decimal/empty/garbage field value to a non-negative
  # integer string. Used by token-display helpers.
  local v="$1"
  v="${v%%.*}"
  case "$v" in
    ''|*[!0-9]*) printf '0' ;;
    *) printf '%s' "$v" ;;
  esac
}
__fmt_token_compact() {
  local n
  n="$(__norm_int "$1")"
  if [ "$n" -lt 1000 ]; then printf '%s' "$n"; return; fi
  if [ "$n" -lt 1000000 ]; then
    local whole=$((n / 1000))
    local rem=$((n - whole * 1000))
    local dec=$((rem / 100))
    if [ "$dec" -eq 0 ]; then printf '%dk' "$whole"; else printf '%d.%dk' "$whole" "$dec"; fi
    return
  fi
  local whole=$((n / 1000000))
  local rem=$((n - whole * 1000000))
  local dec=$((rem / 100000))
  if [ "$dec" -eq 0 ]; then printf '%dM' "$whole"; else printf '%d.%dM' "$whole" "$dec"; fi
}
__fmt_token_full() {
  local n
  n="$(__norm_int "$1")"
  printf '%s' "$n" | awk '{
    s=$0; out=""; n=length(s)
    while (n > 3) { out=","substr(s,n-2,3) out; n -= 3 }
    out=substr(s,1,n) out
    printf "%s", out
  }'
}
__tokens_used() { __field 'context_window.total_input_tokens'; }
__tokens_total() { __field 'context_window.context_window_size'; }
__tokens_remaining() {
  local u t
  u="$(__norm_int "$(__tokens_used)")"
  t="$(__norm_int "$(__tokens_total)")"
  local r=$((t - u))
  if [ "$r" -lt 0 ]; then r=0; fi
  printf '%d' "$r"
}
__tokens_pct_int() {
  local p="$(__field 'context_window.used_percentage')"
  __norm_int "$p"
}
__tick() {
  if [ -n "${STATUSLINE_CLOCK_OVERRIDE:-}" ]; then
    printf '%s' "$STATUSLINE_CLOCK_OVERRIDE"
  else
    date +%s
  fi
}
__rel_time() {
  local target="$1"
  if [ -z "$target" ]; then printf ''; return; fi
  case "$target" in
    ''|*[!0-9.-]*) printf ''; return ;;
  esac
  local t_int="${target%.*}"
  if [ -z "$t_int" ] || [ "$t_int" = "-" ]; then printf ''; return; fi
  local now diff h m s rem
  now=$(__tick)
  diff=$((t_int - now))
  if [ "$diff" -le 0 ]; then printf ''; return; fi
  if [ "$diff" -lt 60 ]; then printf 'T-%ds' "$diff"; return; fi
  if [ "$diff" -lt 3600 ]; then
    m=$((diff/60)); s=$((diff%60))
    printf 'T-%dm%02ds' "$m" "$s"; return
  fi
  h=$((diff/3600)); rem=$(((diff%3600)/60))
  printf 'T-%dh%02dm' "$h" "$rem"
}
# Month-to-date Claude Code cost, estimated by ccusage at API prices. The line
# reads a cache that a background run refreshes every 5 minutes, so it never
# waits on ccusage. Cache line: "<YYYY-MM> <epoch written> <cost in USD>".
MONTH_COST_CACHE="${MONTH_COST_CACHE:-${XDG_CACHE_HOME:-$HOME/.cache}/claude-statusline/month-cost}"
MONTH_COST_TTL="${MONTH_COST_TTL:-300}"
__refresh_month_cost() {
  local month="$1" now="$2" dir lock tmp cost
  dir="${MONTH_COST_CACHE%/*}"
  lock="$dir/refresh.lock"
  mkdir -p "$dir" 2>/dev/null || return 0
  # A refresh killed mid-run leaves its lock behind; drop it after a minute
  if [ -n "$(find "$lock" -maxdepth 0 -mmin +1 2>/dev/null)" ]; then rmdir "$lock" 2>/dev/null; fi
  mkdir "$lock" 2>/dev/null || return 0
  cost="$(ccusage claude monthly --json --offline --since "${month//-/}01" 2>/dev/null \
    | jq -r --arg m "$month" '[.monthly[] | select(.month == $m) | .totalCost] | add // 0' 2>/dev/null)"
  if [ -n "$cost" ]; then
    tmp="$MONTH_COST_CACHE.$$"
    printf '%s %s %s\n' "$month" "$now" "$cost" > "$tmp" && mv "$tmp" "$MONTH_COST_CACHE"
  fi
  rmdir "$lock" 2>/dev/null
}
# Round "2521.93" to whole dollars with integer maths. printf would read the
# decimal point from the locale and reject it under es_ES.
__round_usd() {
  local whole frac
  whole="$(__norm_int "${1%%.*}")"
  frac="${1#"${1%%.*}"}"
  frac="${frac#.}"
  case "${frac:0:1}" in [5-9]) whole=$((whole + 1)) ;; esac
  printf '%d' "$whole"
}
__month_cost() {
  command -v ccusage >/dev/null 2>&1 && command -v jq >/dev/null 2>&1 || return 0
  local month now c_month="" c_at="" c_cost=""
  month="$(date +%Y-%m)"
  now="$(date +%s)"
  if [ -r "$MONTH_COST_CACHE" ]; then
    read -r c_month c_at c_cost < "$MONTH_COST_CACHE" || :
  fi
  c_at="$(__norm_int "$c_at")"
  if [ "$c_month" != "$month" ] || [ $((now - c_at)) -ge "$MONTH_COST_TTL" ]; then
    __refresh_month_cost "$month" "$now" >/dev/null 2>&1 &
  fi
  # Last month's figure is never shown as this month's
  if [ "$c_month" = "$month" ] && [ -n "$c_cost" ]; then printf '%s' "$c_cost"; fi
}
__v="$(__field 'model.display_name')"
__emit '38;5;198' "$__v"
__emit '38;5;198' ' '
__emit '38;5;211' '['
if [ "$(__field 'thinking.enabled')" = 'true' ]; then
  __v="$(__field 'effort.level')"
  __emit '38;5;211' "$__v"
fi
__emit '38;5;211' ']'
__emit '' ' - '
if awk -v v="$(__field 'context_window.used_percentage')" 'BEGIN{exit !(v+0 < 20)}'; then
  if awk -v v="$(__field 'context_window.total_input_tokens')" 'BEGIN{exit !(v+0 > 200000)}'; then
    __v="$(__field 'context_window.used_percentage')"
    __emit '38;5;167' "$__v"
  else
    if awk -v v="$(__field 'context_window.total_input_tokens')" 'BEGIN{exit !(v+0 > 150000)}'; then
      __v="$(__field 'context_window.used_percentage')"
      __emit '38;5;214' "$__v"
    else
      if awk -v v="$(__field 'context_window.total_input_tokens')" 'BEGIN{exit !(v+0 > 10000)}'; then
        __v="$(__field 'context_window.used_percentage')"
        __emit '38;5;226' "$__v"
      else
        __v="$(__field 'context_window.used_percentage')"
        __emit '38;5;114' "$__v"
      fi
    fi
  fi
fi
if awk -v v="$(__field 'context_window.used_percentage')" 'BEGIN{exit !(v+0 > 19.99)}'; then
  __v="$(__field 'context_window.used_percentage')"
  __emit '1;38;2;194;82;82' "$__v"
fi
__emit '2' '%'
__emit '' ' | '
__v="$(__field 'workspace.current_dir')"
__v="$(__basename "$__v")"
__emit '38;2;100;171;255' "$__v"
__emit '38;2;100;171;255' ' '
__out="$(__git_branch)"
__emit '3;38;2;113;224;255' "$__out"
__emit '3;38;2;113;224;255' ' '
__out="$(__month_cost)"
if [ -n "$__out" ]; then
  __emit '' '| '
  __emit '38;5;150' "~\$$(__round_usd "$__out")/mes"
fi

exit 0

