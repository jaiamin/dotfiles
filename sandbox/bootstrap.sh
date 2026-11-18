#!/usr/bin/env bash
# Guest-only setup. Never replaces Docker-managed agent settings or auth files.
set -euo pipefail
if [[ $(uname -s) != Linux || $HOME != /home/agent || $(id -u) != 1000 ]]; then
  echo 'Run this inside a Docker Sandbox as agent, never on your Mac.' >&2
  exit 1
fi
export PATH="$HOME/.local/bin:$PATH"
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
state_dir="$HOME/.local/state/dotfiles"
mkdir -p "$state_dir" "$HOME/.local/bin"

npm_global() {
  local options=(--global --prefix "$HOME/.local")
  local http_proxy=${HTTP_PROXY:-${http_proxy:-}}
  local https_proxy=${HTTPS_PROXY:-${https_proxy:-$http_proxy}}
  [[ -z $http_proxy ]] || options+=(--proxy "$http_proxy")
  [[ -z $https_proxy ]] || options+=(--https-proxy "$https_proxy")
  npm install "${options[@]}" "$@"
}

# Keep a working image-provided runtime; otherwise install a guest-local LTS.
ensure_node() (
  node_major=$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || true)
  if [[ $node_major =~ ^[0-9]+$ ]] && ((node_major >= 22)) \
    && npm --version >/dev/null 2>&1 && npx --version >/dev/null 2>&1; then
    return
  fi
  version=24.22.2
  case $(uname -m) in
    aarch64 | arm64) arch=arm64 ;;
    x86_64) arch=x64 ;;
    *) echo 'Unsupported Node.js architecture.' >&2; exit 1 ;;
  esac
  archive="node-v$version-linux-$arch.tar.gz"
  base="https://nodejs.org/dist/v$version"
  node_tmp=$(mktemp -d)
  trap 'rm -rf -- "$node_tmp"' EXIT
  printf 'Installing guest Node.js %s and npm.\n' "$version"
  curl -fsSL "$base/SHASUMS256.txt" -o "$node_tmp/checksums.txt"
  curl -fsSL "$base/$archive" -o "$node_tmp/$archive"
  (
    cd "$node_tmp"
    awk -v file="$archive" '$2 == file { print; found=1 } END { if (!found) exit 1 }' \
      checksums.txt >selected-checksum
    sha256sum -c selected-checksum
  )
  mkdir -p "$HOME/.local/share/dotfiles" "$HOME/.local/bin"
  tar -xzf "$node_tmp/$archive" -C "$HOME/.local/share/dotfiles"
  node_dir="$HOME/.local/share/dotfiles/node-v$version-linux-$arch"
  for tool in node npm npx; do
    ln -sfn "$node_dir/bin/$tool" "$HOME/.local/bin/$tool"
  done
  node --version
  npm --version
  npx --version
)

setup_browser() (
  command -v agent-browser >/dev/null || npm_global agent-browser
  # Playwright supplies Linux ARM64 builds. Do not rely on auto-discovery.
  npx --yes playwright@1.61.1 install --with-deps chromium
  browser_path=$(find "$HOME/.cache/ms-playwright" -type f -path '*/chrome-linux*/chrome' -print -quit)
  [[ -n $browser_path && -x $browser_path ]] || {
    echo 'Chromium binary not found.' >&2
    exit 1
  }
  mkdir -p "$HOME/.agent-browser"
  # Preserve any other agent-browser settings.
  config="$HOME/.agent-browser/config.json"
  tmp=$(mktemp)
  trap 'rm -f -- "$tmp"' EXIT
  if [[ -f $config ]]; then
    jq --arg path "$browser_path" '.executablePath = $path' "$config" >"$tmp"
  else
    jq -n --arg path "$browser_path" '{executablePath: $path}' >"$tmp"
  fi
  install -m 600 "$tmp" "$config"
  agent-browser open about:blank
  agent-browser close
)

install_from() (
  local installer
  installer=$(mktemp) || exit
  trap 'rm -f -- "$installer"' EXIT
  curl -fsSL --retry 2 "$1" -o "$installer" || exit
  bash "$installer"
)

update_cursor() {
  if [[ -x $HOME/.local/bin/cursor-agent ]] && cursor-agent update; then
    return
  fi
  install_from https://cursor.com/install
}

update_antigravity() {
  if command -v agy >/dev/null; then
    agy update
  else
    install_from https://antigravity.google/cli/install.sh
  fi
}

setup_provider() {
  local binary=$1
  shift
  if [[ $mode == refresh ]] || ! command -v "$binary" >/dev/null; then
    printf '\nInstalling or updating %s\n' "$binary"
    "$@" || return
    hash -r
  fi
  "$binary" --version
}

setup_providers() (
  flock -n 9 || { echo 'Another provider update is running in this sandbox.' >&2; exit 1; }
  local failed=()
  setup_provider codex npm_global --include=optional @openai/codex@latest || failed+=(Codex)
  setup_provider claude install_from https://claude.ai/install.sh || failed+=(Claude)
  setup_provider cursor-agent update_cursor || failed+=(Cursor)
  setup_provider agy update_antigravity || failed+=(Antigravity)
  if [[ ${failed[*]} ]]; then
    printf 'Provider setup failed for %s. Fix the errors above and retry refresh.\n' "${failed[*]}" >&2
    exit 1
  fi
) 9>"$state_dir/providers.lock"

install_gitleaks() (
  local version=8.30.1 arch tmp_dir
  case $(uname -m) in
    aarch64 | arm64) arch=arm64 ;;
    x86_64) arch=x64 ;;
    *) echo 'Unsupported Gitleaks architecture.' >&2; exit 1 ;;
  esac
  local archive="gitleaks_${version}_linux_${arch}.tar.gz"
  local base="https://github.com/gitleaks/gitleaks/releases/download/v$version"
  tmp_dir=$(mktemp -d)
  trap 'rm -rf -- "$tmp_dir"' EXIT
  cd "$tmp_dir"
  curl -fsSL "$base/$archive" -o "$archive"
  curl -fsSL "$base/gitleaks_${version}_checksums.txt" -o checksums.txt
  awk -v file="$archive" '$2 == file { print; found=1 } END { if (!found) exit 1 }' \
    checksums.txt >selected-checksum
  sha256sum -c selected-checksum
  tar -xzf "$archive" gitleaks
  install -m 755 gitleaks "$HOME/.local/bin/gitleaks"
)

link_instructions() {
  local target=$1 path=$2
  if [[ -e $path || -L $path ]]; then
    if [[ $(readlink "$path" || true) != "$target" ]]; then
      printf 'Keeping existing instructions at %s\n' "$path" >&2
    fi
    return
  fi
  ln -s "$target" "$path"
}

if [[ ${1:-} == --browser ]]; then
  ensure_node
  setup_browser
  exit 0
fi

repo=${1-}
browser=${2:-false}
git_name=${3:?Pass Git user name}
git_email=${4:?Pass Git user email}
mode=${5:-create}
workspace=/home/agent/workspace

if [[ $mode == refresh && -z $repo ]]; then
  origin=$(git -C "$workspace" config --local --get remote.origin.url 2>/dev/null) || {
    echo 'No project origin found. Run refresh with OWNER/REPO to finish setup.' >&2
    exit 1
  }
  [[ $origin == https://github.com/* ]] || {
    echo 'Expected a GitHub HTTPS origin. Run refresh with OWNER/REPO to check the checkout.' >&2
    exit 1
  }
  repo=${origin#https://github.com/}
  repo=${repo%.git}
fi
[[ $mode == create || $mode == refresh ]] || { echo 'Expected create or refresh.' >&2; exit 1; }
case $browser in false | true) ;; *)
  echo 'Browser must be false or true.' >&2
  exit 1
  ;;
esac
[[ $repo =~ ^[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+$ && $repo != */. && $repo != */.. ]] || {
  echo 'Expected OWNER/REPO.' >&2
  exit 1
}
command -v apt-get >/dev/null || { echo 'Use a Debian/Ubuntu-based sandbox image.' >&2; exit 1; }
if [[ ! -f $state_dir/tools-v1 ]]; then
  sudo apt-get update
  sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y \
    build-essential python3 libatomic1 util-linux ca-certificates curl git git-lfs gh jq ripgrep unzip shellcheck tar gzip
fi
# Run on refresh too, even when an older tools marker already exists.
ensure_node
if [[ ! -f $state_dir/tools-v1 ]]; then
  command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
  command -v pnpm >/dev/null || npm_global pnpm
  if ! command -v gitleaks >/dev/null; then
    install_gitleaks
  fi
  touch "$state_dir/tools-v1"
fi

# T3 readiness also runs on refresh of an existing managed sandbox.
# New sandboxes receive t3 from Docker's kit; older ones install it here.
if ! command -v t3 >/dev/null; then
  npm_global t3@latest
fi
# Fail provisioning now if a native dependency is missing, rather than timing out in T3.
t3 --version

# sbx sources this for agent sessions and non-interactive SSH shells.
# Preserve existing settings, and let an explicit telemetry preference win.
# shellcheck disable=SC2016
for setting in 'export PATH="$HOME/.local/bin:$PATH"' \
  'export T3CODE_TELEMETRY_ENABLED="${T3CODE_TELEMETRY_ENABLED:-false}"'; do
  if ! sudo grep -Fxq -- "$setting" /etc/sandbox-persistent.sh 2>/dev/null; then
    printf '\n%s\n' "$setting" | sudo tee -a /etc/sandbox-persistent.sh >/dev/null
  fi
done

if [[ ! -e $workspace/.git ]]; then
  # Git refuses a nonempty destination. Never overwrite or clean it automatically.
  git -c 'credential.helper=!gh auth git-credential' clone "https://github.com/$repo.git" "$workspace"
fi
[[ $(git -C "$workspace" rev-parse --show-toplevel) == "$workspace" ]] || {
  echo 'Unexpected repository root.' >&2
  exit 1
}
git -C "$workspace" rev-parse --verify HEAD >/dev/null || {
  echo 'Repository needs an initial commit.' >&2
  exit 1
}
origin=$(git -C "$workspace" config --get remote.origin.url)
[[ $origin == "https://github.com/$repo.git" || $origin == "https://github.com/$repo" ]] || {
  echo 'Existing checkout belongs to another repository; leaving it untouched.' >&2
  exit 1
}
# Scope the HTTPS helper to this checkout, without replacing global auth settings.
git -C "$workspace" config credential.https://github.com.helper '!gh auth git-credential'
# Portable Git hook; preserve repository-installed hooks and custom hook managers.
hook=$(git -C "$workspace" rev-parse --path-format=absolute --git-path hooks/pre-commit)
if [[ -z $(git -C "$workspace" config --get core.hooksPath || true) && ! -e $hook && ! -L $hook ]]; then
  mkdir -p "$(dirname "$hook")"
  cat >"$hook" <<'HOOK'
#!/usr/bin/env bash
export PATH="$HOME/.local/bin:$PATH"
exec gitleaks git --pre-commit --staged --redact --no-banner
HOOK
  chmod 755 "$hook"
fi

# Task ownership belongs to T3 Code or ordinary Git worktrees.
# Never switch or reset the primary checkout during a refresh.
git -C "$workspace" config pull.ff only

# Share the generated guidance while preserving user-authored instructions.
mkdir -p "$HOME/.config/dotfiles" "$HOME/.config/git" "$HOME/.config/opencode" \
  "$HOME/.claude" "$HOME/.codex" "$HOME/.gemini"
instructions="$HOME/.config/dotfiles/AGENTS.md"
[[ ! -d $instructions ]] || { echo 'Expected an instructions file, found a directory.' >&2; exit 1; }
# Publish a complete file so an agent starting during refresh sees valid guidance.
tmp=$(mktemp "${instructions}.XXXXXX")
trap 'rm -f -- "$tmp"' EXIT
cat "$source_dir/base.md" "$source_dir/AGENTS.md" >"$tmp"
mv -f -- "$tmp" "$instructions"
trap - EXIT
link_instructions ../.config/dotfiles/AGENTS.md "$HOME/.claude/CLAUDE.md"
link_instructions ../.config/dotfiles/AGENTS.md "$HOME/.codex/AGENTS.md"
link_instructions ../dotfiles/AGENTS.md "$HOME/.config/opencode/AGENTS.md"
link_instructions ../.config/dotfiles/AGENTS.md "$HOME/.gemini/AGENTS.md"
install -m 644 "$source_dir/gitignore" "$HOME/.config/git/ignore"
git config --global user.name "$git_name"
git config --global user.email "$git_email"
git config --global init.defaultBranch main
git config --global push.autoSetupRemote true
git config --global fetch.prune true
git config --global core.excludesFile "$HOME/.config/git/ignore"

setup_providers
if [[ $browser == true ]]; then
  setup_browser
fi
printf 'Ready: %s. Use one writer per task branch/worktree.\n' "$workspace"
