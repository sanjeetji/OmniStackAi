#!/usr/bin/env bash
set -euo pipefail

repo_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"

if git -C "$repo_root" ls-files \
  | rg -v '(^|/)\.env\.example$' \
  | rg -q '(^|/)(\.env($|\.)|.*\.(pem|key|p12|pfx|jks|keystore)$|credentials\.json$|secrets?\.(yaml|yml|json)$)'; then
  printf 'Tracked path violates the secret exclusion policy.\n'
  exit 1
fi

if rg -n --hidden --glob '!R_&_D/**' --glob '!.git/**' --glob '!.env.example' \
  '(AKIA[0-9A-Z]{16}|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----|sk-[A-Za-z0-9]{20,})' \
  "$repo_root"; then
  printf 'Potential secret material detected.\n'
  exit 1
fi

printf 'Stage 0 secret-policy check passed.\n'
