#!/usr/bin/env bash
# Guest-only optional adapter. The ordinary SSH path does not need Orca installed.
set -euo pipefail
die() { printf '%s\n' "$*" >&2; exit 1; }
[[ $(uname -s) == Linux && $HOME == /home/agent && $(id -u) == 1000 ]] || die 'Run only inside a Docker Sandbox as agent.'
port=${1:-6768}
[[ $port =~ ^[0-9]{4,5}$ && $port -ge 1024 && $port -le 65535 ]] || die 'Invalid port.'
export PATH="$HOME/.local/bin:$PATH"
state="$HOME/.local/state/dotfiles/orca"
mkdir -p "$state"
chmod 700 "$state"
if ! command -v orca-ide >/dev/null; then
  case $(uname -m) in aarch64|arm64) arch=arm64 ;; x86_64) arch=amd64 ;; *) die 'Unsupported architecture.' ;; esac
  tmp=$(mktemp -d)
  trap 'rm -rf -- "$tmp"' EXIT
  curl -fsSL https://api.github.com/repos/stablyai/orca/releases/latest -o "$tmp/release.json"
  url=$(jq -er --arg suffix "_${arch}.deb" \
    '[.assets[] | select(.name | endswith($suffix)) | .browser_download_url] | if length == 1 then .[0] else error("Expected one Orca package") end' "$tmp/release.json")
  [[ $url == https://github.com/stablyai/orca/releases/download/* ]] || die 'Unexpected release URL.'
  curl -fsSL "$url" -o "$tmp/orca.deb"
  # apt's _apt user must be able to read the downloaded package.
  chmod 755 "$tmp"
  chmod 644 "$tmp/orca.deb"
  sudo apt-get update
  sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y "$tmp/orca.deb"
fi
command -v orca-ide >/dev/null || die 'Orca CLI was not installed.'
command -v flock >/dev/null || die 'Missing flock (util-linux).'
lock="$state/server.lock"
if flock -n "$lock" true; then
  umask 077
  # A foreground serve process owns the lock. Docker detached mode keeps the VM up.
  nohup flock -n "$lock" orca-ide serve --port "$port" \
    --pairing-address 127.0.0.1 > "$state/server.log" 2>&1 < /dev/null &
  printf '%s\n' "$port" > "$state/port"
  printf 'Orca server starting.\n'
else
  [[ $(cat "$state/port") == "$port" ]] || die 'Server already runs on another port. Stop it before changing ports.'
  printf 'Orca server already running.\n'
fi
printf 'Pair from the Mac on localhost:%s. Keep client and server versions compatible.\n' "$port"
printf 'Private pairing URL and startup errors: %s/server.log\n' "$state"
printf 'Do not commit or share that log.\n'
