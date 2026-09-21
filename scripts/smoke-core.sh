#!/usr/bin/env bash
# Live smoke test of the platform's core loop, through the console exactly as the Studio calls it:
#   register -> create a project from a prompt only -> stream the build -> the project is renamed
#   from "Untitled project" -> /opened -> turns + files exist -> a chat edit commits.
#
# Needs the platform running (./scripts/omnistack.sh up) and a working model provider.
# It makes real model calls (one build, one edit). It is never part of `task verify`.
#
#   ./scripts/smoke-core.sh                       # uses http://127.0.0.1:4321
#   OMNISTACK_CONSOLE_URL=http://host:4321 ./scripts/smoke-core.sh
set -uo pipefail

B="${OMNISTACK_CONSOLE_URL:-http://127.0.0.1:4321}"
PROMPT="${SMOKE_PROMPT:-A simple habit tracker with habits and daily check-ins}"
EDIT_PROMPT="${SMOKE_EDIT_PROMPT:-Add a notes field to each check-in}"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
jar="${SMOKE_COOKIE_JAR:-$work/cookies}"  # set SMOKE_COOKIE_JAR to reuse the session afterwards
failures=0

check() {  # check <label> <actual> <expected-regex>
  if [[ "$2" =~ $3 ]]; then
    printf '  \033[32mpass\033[0m  %-44s %s\n' "$1" "$2"
  else
    printf '  \033[31mFAIL\033[0m  %-44s %s (want %s)\n' "$1" "$2" "$3"
    failures=$((failures + 1))
  fi
}

json() { python3 -c "import json,sys; d=json.load(open('$1')); print(eval('d'+sys.argv[1]) if True else '')" "$2" 2>/dev/null; }

email="smoke-$(date +%s)@example.com"
code=$(curl -s -c "$jar" -o /dev/null -w '%{http_code}' -H 'Content-Type: application/json' \
  -d "{\"email\":\"$email\",\"name\":\"Smoke Test\",\"password\":\"SmokeTest12345!\"}" "$B/api/auth/register")
check "register" "$code" '^201$'

code=$(curl -s -b "$jar" -o "$work/project.json" -w '%{http_code}' -H 'Content-Type: application/json' \
  -d "{\"prompt\":\"$PROMPT\"}" "$B/api/projects")
check "create project from a prompt only" "$code" '^201$'
project_id="$(json "$work/project.json" "['id']")"
check "new project starts as 'Untitled project'" "$(json "$work/project.json" "['name']")" '^Untitled project$'

started=$(date +%s)
code=$(curl -N -s -b "$jar" -o "$work/stream.txt" -w '%{http_code}' --max-time 600 \
  -H 'Content-Type: application/json' -d "{\"prompt\":\"$PROMPT\",\"mention_skills\":[]}" \
  "$B/api/projects/$project_id/build/stream")
elapsed=$(( $(date +%s) - started ))
check "build stream status" "$code" '^200$'
check "build stream reached done (${elapsed}s)" "$(grep -c '"phase": *"done"' "$work/stream.txt" || true)" '^[1-9]'
check "build stream had no error frame" "$(grep -c '"phase": *"error"' "$work/stream.txt" || true)" '^0$'
if grep -q '"phase": *"error"' "$work/stream.txt"; then grep '"phase": *"error"' "$work/stream.txt" | head -2 | cut -c1-240; fi

curl -s -b "$jar" -o "$work/after.json" "$B/api/projects/$project_id"
check "project renamed after the build" "$(json "$work/after.json" "['name']")" '^.+$'
check "project name is no longer the placeholder" "$(json "$work/after.json" "['name']")" '^([^U]|U[^n]|Un[^t])'
check "file count recorded" "$(json "$work/after.json" "['file_count']")" '^[1-9]'

code=$(curl -s -b "$jar" -o /dev/null -w '%{http_code}' -X POST "$B/api/projects/$project_id/opened")
check "POST /opened" "$code" '^2..$'

curl -s -b "$jar" -o "$work/turns.json" "$B/api/projects/$project_id/turns"
check "chat turns persisted" "$(json "$work/turns.json" "['turns'].__len__()")" '^[1-9]'
curl -s -b "$jar" -o "$work/files.json" "$B/api/projects/$project_id/files"
check "files listed" "$(json "$work/files.json" "['files'].__len__()")" '^[1-9]'

if [[ "${SMOKE_SKIP_EDIT:-0}" != "1" ]]; then
  code=$(curl -s -b "$jar" -o "$work/edit.json" -w '%{http_code}' --max-time 600 \
    -H 'Content-Type: application/json' -d "{\"prompt\":\"$EDIT_PROMPT\"}" \
    "$B/api/projects/$project_id/edit")
  check "chat edit" "$code" '^200$'
  if [[ "$code" != "200" ]]; then head -c 400 "$work/edit.json"; echo; fi
  check "chat edit produced a commit" "$(json "$work/edit.json" "['commit_sha']")" '^[0-9a-f]{7,}$'
fi

printf '\nproject: %s\n' "$project_id"
if (( failures > 0 )); then
  printf '\033[31m%d check(s) failed.\033[0m\n' "$failures"
  exit 1
fi
printf '\033[32mCore loop passed.\033[0m\n'
