#!/usr/bin/env bash
# Host-side provisioning only. Agents and development tools run in the sandbox.
set -euo pipefail
die() {
  printf '%s\n' "$*" >&2
  exit 1
}
usage='Usage: manage.sh create NAME OWNER/REPO AGENT [false|true] [-- SBX_OPTIONS...]
       manage.sh refresh NAME [OWNER/REPO] [false|true]
       manage.sh check|ports|network-open|network-restore NAME
       manage.sh network-allow NAME HOST[:PORT]
       manage.sh publish|unpublish NAME HOST_PORT SANDBOX_PORT
       manage.sh auth-set|auth-remove NAME openai|anthropic'
[[ $# -ge 2 ]] || die "$usage"
action=$1 name=$2
shift 2
label='[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?'
[[ ${#name} -ge 2 && ${#name} -le 63 && $name != default && $name =~ ^$label(\.$label)*$ ]] ||
  die 'Invalid sandbox name. Use 2–63 letters, numbers, hyphens, or periods.'
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
root=$(cd -- "$here/.." && pwd)
command -v sbx >/dev/null || die 'Install Docker Sandboxes (sbx) first.'

managed_sandbox() {
  sbx exec -u 1000 "$name" test -f /home/agent/.config/dotfiles/managed ||
    die "Expected a dotfiles-managed sandbox: $name"
}

validate_port() {
  if [[ ! $1 =~ ^[1-9][0-9]{0,4}$ ]] || (( $1 > 65535 )); then
    die "Invalid port: $1"
  fi
}

port_command() {
  local command=$1
  shift
  if sbx port --help >/dev/null 2>&1; then
    sbx port "$command" "$name" "$@"
  elif [[ $command == ls ]]; then
    sbx ports "$name"
  else
    sbx ports "$name" "--$command" "$@"
  fi
}

provider_key() {
  local host key placeholder=''
  case $1 in
    openai) host=api.openai.com; key=OPENAI_API_KEY ;;
    anthropic) host=api.anthropic.com; key=ANTHROPIC_API_KEY ;;
    *) die 'Choose openai or anthropic.' ;;
  esac
  if [[ $action == auth-set ]]; then
    local secret=''
    IFS= read -r -s -p "$1 API key: " secret || true
    if [[ -t 0 ]]; then printf '\n' >&2; fi
    [[ -n $secret ]] || die 'Enter an API key to continue.'
    placeholder="sbx-cs-$(openssl rand -hex 12)"
    sbx policy allow network --sandbox "$name" "$host:443"
    printf '%s' "$secret" | sbx secret set-custom --sandbox "$name" --host "$host" --env "$key" \
      --placeholder "$placeholder" --value-stdin
    unset secret
  else
    sbx secret rm --sandbox "$name" --host "$host" --env-name "$key"
  fi
  # shellcheck disable=SC2016
  sbx exec -u root "$name" sh -eu -c '
    file=/etc/sandbox-persistent.sh
    [ -f "$file" ] || [ -n "$2" ] || exit 0
    touch "$file"
    sed -i "/^export $1=sbx-cs-[[:xdigit:]]\{24\}$/d" "$file"
    if [ -n "$2" ]; then printf "\nexport %s=%s\n" "$1" "$2" >>"$file"; fi
  ' sh "$key" "$placeholder"
}

check_sandbox() {
  command -v ssh >/dev/null || die 'Missing SSH client.'
  managed_sandbox
  # Exercise the same non-interactive SSH path used by the T3 desktop app.
  ssh -o BatchMode=yes -o ConnectTimeout=10 "$name.sbx" 'bash -s' <<'CHECK'
set -euo pipefail
[[ $(uname -s) == Linux && $HOME == /home/agent && $(id -u) == 1000 ]] || {
  echo 'Expected a Docker Sandbox running as agent.' >&2
  exit 1
}
test -f "$HOME/.config/dotfiles/managed"
test -f "$HOME/.config/dotfiles/AGENTS.md"
git -C /home/agent/workspace rev-parse --verify HEAD >/dev/null
git -C /home/agent/workspace remote get-url origin >/dev/null
failed=0
for tool in node npm codex claude cursor-agent agy; do
  printf '%s: ' "$tool"
  if ! "$tool" --version; then
    printf 'Check failed for %s. Run manage.sh refresh.\n' "$tool" >&2
    failed=1
  fi
done
exit "$failed"
CHECK
}

case $action in
  check | ports | network-open | network-restore)
    [[ $# -eq 0 ]] || die "$usage"
    case $action in
      check) check_sandbox ;;
      ports) port_command ls ;;
      network-open) sbx policy allow network --sandbox "$name" --protocol tcp,udp '**' ;;
      network-restore) sbx policy rm network --sandbox "$name" --resource '**' ;;
    esac
    exit
    ;;
  network-allow)
    [[ $# -eq 1 ]] || die "$usage"
    [[ $1 =~ ^[A-Za-z0-9][A-Za-z0-9.-]*[A-Za-z0-9](:[1-9][0-9]{0,4})?$ && $1 == *.* ]] || die 'Expected a hostname or hostname:port.'
    if [[ $1 == *:* ]]; then validate_port "${1##*:}"; fi
    sbx policy allow network --sandbox "$name" "$1"
    exit
    ;;
  publish | unpublish)
    [[ $# -eq 2 ]] || die "$usage"
    validate_port "$1"
    validate_port "$2"
    port_command "$action" "127.0.0.1:$1:$2"
    exit
    ;;
  auth-set | auth-remove)
    [[ $# -eq 1 ]] || die "$usage"
    provider_key "$1"
    exit
    ;;
  create | refresh) ;;
  *) die "$usage" ;;
esac

repo=''
if [[ $action == create || $# -gt 0 && $1 != true && $1 != false ]]; then
  [[ $# -gt 0 ]] || die "$usage"
  repo=$1
  shift
  [[ $repo =~ ^[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+$ && $repo != */. && $repo != */.. ]] || die 'Expected OWNER/REPO.'
fi
if [[ $action == create ]]; then
  [[ $# -ge 1 && -n $1 && $1 != -* ]] || die "$usage"
  agent=$1
  shift
fi
browser=false
if [[ $# -gt 0 && $1 != -- ]]; then
  browser=$1
  shift
fi
case $browser in false | true) ;; *) die 'Browser must be false or true.' ;; esac
if [[ $# -gt 0 ]]; then
  [[ $1 == -- ]] || die "$usage"
  shift
fi
[[ $action != refresh || $# -eq 0 ]] || die "$usage"
# Only resource, template, and kit options may be forwarded. No workspace mounts.
# Keep this nonempty: macOS's Bash 3.2 treats empty arrays as unset under nounset.
# Built-in agents resolve to v3 kits; every companion kit must use v3 too.
options=(--cpus 4 --memory 4g --skills readonly)
while [[ $# -gt 0 ]]; do
  case $1 in
    --cpus | --memory | --template | --pull | --kit | --kit-arg | --kit-args-file)
      [[ $# -ge 2 && $2 != -* ]] || die "Missing value for $1"
      options+=("$1" "$2")
      shift 2
      ;;
    *) die "Unsupported creation option: $1" ;;
  esac
done
command -v git >/dev/null || die 'Missing git.'
git_name=$(git config --file "$root/dot_gitconfig" user.name)
git_email=$(git config --file "$root/dot_gitconfig" user.email)
[[ -n $git_name && -n $git_email ]] || die 'Set your Git identity in dot_gitconfig.'
for file in bootstrap.sh AGENTS.md; do
  [[ -f $here/$file ]] || die "Missing sandbox/$file"
done
if [[ $action == create ]]; then
  existing=$(sbx ls -q)
  while IFS= read -r item; do
    [[ $item != "$name" ]] || die "Sandbox already exists: $name. Use refresh or connect to it."
  done <<<"$existing"
  # Omitting the workspace path is deliberate. Docker owns agent/auth configuration.
  sbx create "$agent" --name "$name" "${options[@]}"
else
  managed_sandbox
fi

destination=/home/agent/.config/dotfiles/source
sbx exec -u 1000 "$name" mkdir -p "$destination"
sbx exec -u 1000 "$name" touch /home/agent/.config/dotfiles/managed

# Installer and sign-in endpoints. Scope to the named sandbox.
hosts=(
  'github.com,api.github.com,raw.githubusercontent.com,release-assets.githubusercontent.com,objects.githubusercontent.com'
  'registry.npmjs.org,nodejs.org,astral.sh,pypi.org,files.pythonhosted.org'
  'archive.ubuntu.com,security.ubuntu.com,ports.ubuntu.com,deb.debian.org,security.debian.org,download.docker.com,cli.github.com'
  'context7.com,mcp.context7.com,storage.googleapis.com'
  'api.openai.com,auth.openai.com,chatgpt.com'
  'api.anthropic.com,claude.ai,claude.com,platform.claude.com,downloads.claude.ai'
  'cursor.com,downloads.cursor.com,**.cursor.sh,*.cursorapi.com,accounts.spacex.ai,accounts.x.ai'
  'antigravity.google,antigravity-cli-auto-updater-974169037036.us-central1.run.app'
  'accounts.google.com,oauth2.googleapis.com,cloudcode-pa.googleapis.com,daily-cloudcode-pa.googleapis.com,antigravity.googleapis.com,www.googleapis.com'
)
if [[ $browser == true ]]; then
  hosts+=('cdn.playwright.dev,playwright.download.prss.microsoft.com')
fi
(IFS=,; sbx policy allow network --sandbox "$name" "${hosts[*]}")

for file in bootstrap.sh AGENTS.md; do
  sbx cp "$here/$file" "$name:$destination/$file"
done
sbx cp "$root/dot_codex/AGENTS.md" "$name:$destination/base.md"
sbx cp "$root/dot_config/git/ignore" "$name:$destination/gitignore"
sbx exec -u 1000 "$name" bash "$destination/bootstrap.sh" \
  "$repo" "$browser" "$git_name" "$git_email" "$action"
printf '\nSSH host: %s.sbx\nProject path: /home/agent/workspace\n' "$name"
