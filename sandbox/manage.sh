#!/usr/bin/env bash
# Host-side provisioning only. Agents and development tools run in the sandbox.
set -euo pipefail
die() {
  printf '%s\n' "$*" >&2
  exit 1
}
usage='Usage: manage.sh create NAME OWNER/REPO AGENT [false|true] [-- SBX_OPTIONS...]
       manage.sh refresh NAME OWNER/REPO [false|true]
       manage.sh orca NAME [PORT]'
[[ $# -ge 2 ]] || die "$usage"
action=$1 name=$2
shift 2
[[ $name =~ ^[a-z][a-z0-9-]{1,47}$ && $name != default ]] || die 'Invalid sandbox name.'
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
root=$(cd -- "$here/.." && pwd)
command -v sbx >/dev/null || die 'Install Docker Sandboxes (sbx) first.'

if [[ $action == orca ]]; then
  [[ $# -le 1 ]] || die "$usage"
  port=${1:-6768}
  [[ $port =~ ^[1-9][0-9]{3,4}$ && $port -ge 1024 && $port -le 65535 ]] || die 'Invalid port.'
  sbx exec -u 1000 "$name" -- test -f /home/agent/.config/dotfiles/managed
  sbx run --detach --name "$name"
  sbx exec -u 1000 "$name" -- mkdir -p /home/agent/.config/dotfiles/source
  sbx cp "$here/orca.sh" "$name:/home/agent/.config/dotfiles/source/orca.sh"
  sbx ports "$name" --publish "$port:$port"
  sbx exec -u 1000 "$name" -- bash /home/agent/.config/dotfiles/source/orca.sh "$port"
  exit
fi

[[ $action == create || $action == refresh ]] || die "$usage"
[[ $# -ge 1 ]] || die "$usage"
repo=$1
shift
[[ $repo =~ ^[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+$ && $repo != */. && $repo != */.. ]] || die 'Expected OWNER/REPO.'
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
  # Explicit setup/service domains; keep the rest of the sandbox policy intact.
  sbx policy allow network --sandbox "$name" \
    'github.com,api.github.com,raw.githubusercontent.com,release-assets.githubusercontent.com,objects.githubusercontent.com,registry.npmjs.org,astral.sh,pypi.org,files.pythonhosted.org,archive.ubuntu.com,security.ubuntu.com,ports.ubuntu.com,deb.debian.org,security.debian.org,cdn.playwright.dev,playwright.download.prss.microsoft.com,storage.googleapis.com,context7.com,mcp.context7.com'
else
  sbx exec -u 1000 "$name" -- test -f /home/agent/.config/dotfiles/managed
fi
destination=/home/agent/.config/dotfiles/source
sbx exec -u 1000 "$name" -- mkdir -p "$destination"
sbx exec -u 1000 "$name" -- touch /home/agent/.config/dotfiles/managed
for file in bootstrap.sh AGENTS.md; do
  sbx cp "$here/$file" "$name:$destination/$file"
done
sbx cp "$root/dot_codex/AGENTS.md" "$name:$destination/base.md"
sbx cp "$root/dot_config/git/ignore" "$name:$destination/gitignore"
sbx exec -u 1000 "$name" -- bash "$destination/bootstrap.sh" \
  "$repo" "$browser" "$git_name" "$git_email"
printf '\nSSH: %s.sbx (user _default_user_, no identity file)\n' "$name"
printf 'Remote repository: /home/agent/workspace\n'
printf 'Orca full runtime, optional beta: bash sandbox/manage.sh orca %s\n' "$name"
