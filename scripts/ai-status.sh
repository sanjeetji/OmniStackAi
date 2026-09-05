#!/usr/bin/env bash
set -euo pipefail

repo_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
task_id="$(awk -F': ' '$1 == "task_id" {print $2; exit}' "$repo_root/.ai/CURRENT_TASK.yaml")"
task_status="$(awk -F': ' '$1 == "status" {print $2; exit}' "$repo_root/.ai/CURRENT_TASK.yaml")"
phase="$(awk -F': ' '$1 == "phase" {print $2; exit}' "$repo_root/.ai/CURRENT_TASK.yaml")"
next_action="$(awk -F': ' '$1 == "next_action" {sub($1 FS, ""); print; exit}' "$repo_root/.ai/CURRENT_TASK.yaml")"
branch="$(git -C "$repo_root" branch --show-current)"
head_sha="$(git -C "$repo_root" rev-parse --verify HEAD 2>/dev/null || printf 'no-commit')"

printf 'Phase: %s\n' "$phase"
printf 'Task: %s (%s)\n' "$task_id" "$task_status"
printf 'Branch: %s\n' "$branch"
printf 'HEAD: %s\n' "$head_sha"
printf 'Next action: %s\n' "$next_action"

