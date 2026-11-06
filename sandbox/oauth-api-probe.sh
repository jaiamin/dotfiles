#!/usr/bin/env bash
# Opt-in auth probe. Never updates an existing project sandbox or global secrets.
set -euo pipefail

die() { printf '%s\n' "$*" >&2; exit 1; }
usage='Usage: oauth-api-probe.sh create|configure|verify [codex-api-probe[-SUFFIX]]'
[[ $# -ge 1 && $# -le 2 ]] || die "$usage"
action=$1
name=${2:-codex-api-probe}
case $action in create | configure | verify) ;; *) die "$usage" ;; esac
[[ $name =~ ^codex-api-probe(-[a-z0-9][a-z0-9-]*)?$ && ${#name} -le 48 ]] ||
  die 'Only dedicated codex-api-probe names are allowed; project sandboxes are refused.'
command -v sbx >/dev/null || die 'Install Docker Sandboxes first.'
version=$(sbx --version)
[[ $version =~ v([0-9]+)\.([0-9]+)\.([0-9]+) ]] || die 'Cannot identify the sbx version.'
((BASH_REMATCH[1] > 0 || BASH_REMATCH[2] >= 51)) || die 'This v3 kit probe requires sbx 0.51.0 or newer.'
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
marker=/home/agent/.config/dotfiles/oauth-api-probe

if [[ $action == create ]]; then
  existing=$(sbx ls -q)
  while IFS= read -r item; do
    [[ $item != "$name" ]] || die "Sandbox $name already exists. Use configure or verify; it will not be recreated."
  done <<<"$existing"
  # Source builds use sbx's builder sandbox when host Docker is unavailable.
  sbx create "$here/kits/codex-oauth" --name "$name" --cpus 2 --memory 4g --skills off
  sbx exec -u 1000 "$name" -- mkdir -p "$marker"
  sbx exec -u 1000 "$name" -- touch "$marker/created"
fi

# A name alone is not proof that this helper created the sandbox.
sbx exec -u 1000 "$name" -- test -f "$marker/created"
if [[ $action == create || $action == configure ]]; then
  if ! sbx exec -u 1000 "$name" -- sh -c 'command -v python3 >/dev/null'; then
    sbx exec -u root "$name" -- sh -c \
      'set -eu; apt-get update; DEBIAN_FRONTEND=noninteractive apt-get install -y python3 ca-certificates'
  fi
  printf '\nEnter your OpenAI platform API key at the sbx prompt. It is stored only for %s.\n' "$name"
  printf 'Approve project-openai only for api.openai.com when the kit asks.\n'
  if ! sbx secret set project-openai --sandbox "$name"; then
    die "API-key setup failed. The probe is preserved; retry: bash $here/oauth-api-probe.sh configure $name"
  fi
  if ! sbx exec -u 1000 "$name" -- test -f "$marker/project-kit-added"; then
    if ! sbx kit add "$name" "$here/kits/project-openai"; then
      die "Kit setup failed. The probe and its scoped secret are preserved; retry: bash $here/oauth-api-probe.sh configure $name"
    fi
    sbx exec -u 1000 "$name" -- touch "$marker/project-kit-added"
  fi
fi

sbx exec -u 1000 "$name" -- test -f "$marker/project-kit-added"
sbx cp "$here/oauth_api_verify.py" "$name:$marker/verify.py"
printf '\nTesting one small project API request and one Codex OAuth turn.\n'
sbx exec -u 1000 "$name" -- python3 "$marker/verify.py"
printf '\nBoth checks passed in %s. Your project sandbox and default setup were not changed.\n' "$name"
