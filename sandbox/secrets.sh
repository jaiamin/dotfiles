#!/usr/bin/env bash
# Host-side Navi helper. Real values are entered only at sbx's secret prompt.
set -euo pipefail
die() { printf '%s\n' "$*" >&2; exit 1; }
[[ $# -eq 4 ]] || die 'Usage: secrets.sh set|remove SANDBOX ENV HOST'
action=$1 sandbox=$2 key_name=$3 api_host=$4
case $action in set | remove) ;; *) die 'Expected set or remove.' ;; esac
[[ $sandbox =~ ^[A-Za-z0-9][A-Za-z0-9.-]+$ && $sandbox != default ]] || die 'Invalid sandbox name.'
[[ $key_name =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || die 'Invalid environment variable name.'
[[ $api_host =~ ^(\*\.)?[A-Za-z0-9][A-Za-z0-9.-]*$ ]] || die 'Use an API hostname without a URL scheme, path, or port.'
api_host=$(printf '%s' "$api_host" | tr '[:upper:]' '[:lower:]')
command -v sbx >/dev/null || die 'Install Docker Sandboxes first.'

persist() {
  # Variables in the command string are evaluated by the guest shell.
  # shellcheck disable=SC2016
  sbx exec -u root "$sandbox" -- sh -c \
    'set -eu; f=/etc/sandbox-persistent.sh; touch "$f"; sed -i "/^export $1=/d" "$f"; printf "\nexport %s=%s\n" "$1" "$2" >> "$f"' \
    _ "$key_name" "$1"
}
remove_export() {
  # shellcheck disable=SC2016
  sbx exec -u root "$sandbox" -- sh -c \
    'set -eu; f=/etc/sandbox-persistent.sh; if test -f "$f"; then sed -i "/^export $1=/d" "$f"; fi' _ "$key_name"
}

routing=custom
if [[ $api_host == api.openai.com ]]; then
  # Connection failures abort; they must not silently select the custom path.
  routing=$(sbx exec -u 1000 "$sandbox" -- sh -c \
    'if test -f /home/agent/.config/dotfiles/project-openai || test -f /home/agent/.config/dotfiles/oauth-api-probe/created-with-api-kit; then printf service; else printf custom; fi')
  [[ $routing == service || $routing == custom ]] || die 'Could not identify sandbox API routing.'
fi

if [[ $routing == service ]]; then
  if [[ $action == set ]]; then
    sbx secret set project-openai --sandbox "$sandbox"
    # Standard and custom SDK variable names can carry the same public sentinel.
    persist proxy-managed
  else
    sbx secret rm project-openai --sandbox "$sandbox"
    remove_export
  fi
elif [[ $action == set ]]; then
  command -v openssl >/dev/null || die 'OpenSSL is required for a custom placeholder.'
  # Do not register/rotate a secret if its destination cannot be allowed.
  sbx policy allow network --sandbox "$sandbox" "$api_host:443"
  placeholder="sbx-cs-$(openssl rand -hex 12)"
  sbx secret set-custom --sandbox "$sandbox" --host "$api_host" --env "$key_name" --placeholder "$placeholder"
  persist "$placeholder"
else
  sbx secret rm --sandbox "$sandbox" --host "$api_host" --env-name "$key_name"
  remove_export
fi
