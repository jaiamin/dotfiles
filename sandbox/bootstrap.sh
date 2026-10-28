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

if [[ ${1:-} == --browser ]]; then
  command -v agent-browser >/dev/null || npm install --global --prefix "$HOME/.local" agent-browser
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
  exit 0
fi

repo=${1:?Pass OWNER/REPO}
browser=${2:-false}
git_name=${3:?Pass Git user name}
git_email=${4:?Pass Git user email}
case $browser in false | true) ;; *)
  echo 'Browser must be false or true.' >&2
  exit 1
  ;;
esac
command -v apt-get >/dev/null || {
  echo 'This tool bootstrap requires a Debian/Ubuntu-based image. Use the selected kit directly for other distributions.' >&2
  exit 1
}
[[ $repo =~ ^[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+$ && $repo != */. && $repo != */.. ]] || exit 1
if [[ ! -f $state_dir/tools-v1 ]]; then
  sudo apt-get update
  sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y \
    build-essential python3 libatomic1 util-linux ca-certificates curl git git-lfs gh jq ripgrep unzip shellcheck
  if ! command -v node >/dev/null || ! command -v npm >/dev/null; then
    echo 'Expected Node/npm in the Docker agent template.' >&2
    exit 1
  fi
  command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
  command -v pnpm >/dev/null || npm install --global --prefix "$HOME/.local" pnpm
  if ! command -v gitleaks >/dev/null; then
    version=8.30.1
    case $(uname -m) in aarch64 | arm64) arch=arm64 ;; x86_64) arch=x64 ;; *)
      echo 'Unsupported Gitleaks architecture.' >&2
      exit 1
      ;;
    esac
    archive="gitleaks_${version}_linux_${arch}.tar.gz"
    tmp_dir=$(mktemp -d)
    trap 'rm -rf -- "$tmp_dir"' EXIT
    base="https://github.com/gitleaks/gitleaks/releases/download/v$version"
    curl -fsSL "$base/$archive" -o "$tmp_dir/$archive"
    curl -fsSL "$base/gitleaks_${version}_checksums.txt" -o "$tmp_dir/checksums.txt"
    (
      cd "$tmp_dir"
      awk -v file="$archive" '$2 == file { print; found=1 } END { if (!found) exit 1 }' checksums.txt >selected-checksum
      sha256sum -c selected-checksum
    )
    tar -xzf "$tmp_dir/$archive" -C "$tmp_dir" gitleaks
    install -m 755 "$tmp_dir/gitleaks" "$HOME/.local/bin/gitleaks"
    rm -rf -- "$tmp_dir"
    trap - EXIT
  fi
  # sbx sources this for agent sessions and interactive shells. Preserve its contents.
  # The persistent guest shell must expand these variables at session startup.
  # shellcheck disable=SC2016
  path_line='export PATH="$HOME/.local/bin:$PATH"'
  if ! sudo grep -Fxq -- "$path_line" /etc/sandbox-persistent.sh 2>/dev/null; then
    printf '\n%s\n' "$path_line" | sudo tee -a /etc/sandbox-persistent.sh >/dev/null
  fi
  touch "$state_dir/tools-v1"
fi

# One generated instruction file, shared by all supported agent locations.
mkdir -p "$HOME/.config/dotfiles" "$HOME/.claude" "$HOME/.codex" "$HOME/.config/opencode" "$HOME/.config/git"
cat "$source_dir/base.md" "$source_dir/AGENTS.md" >"$HOME/.config/dotfiles/AGENTS.md"
ln -sfn ../.config/dotfiles/AGENTS.md "$HOME/.claude/CLAUDE.md"
ln -sfn ../.config/dotfiles/AGENTS.md "$HOME/.codex/AGENTS.md"
ln -sfn ../dotfiles/AGENTS.md "$HOME/.config/opencode/AGENTS.md"
install -m 644 "$source_dir/gitignore" "$HOME/.config/git/ignore"
git config --global user.name "$git_name"
git config --global user.email "$git_email"
git config --global init.defaultBranch main
git config --global push.autoSetupRemote true
git config --global fetch.prune true
git config --global core.excludesFile "$HOME/.config/git/ignore"

workspace=/home/agent/workspace
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

# Task ownership belongs to Orca, the selected ADE, or ordinary Git worktrees.
# Never switch or reset the primary checkout during a refresh.
git -C "$workspace" config pull.ff only
if [[ $browser == true ]]; then
  bash "$source_dir/bootstrap.sh" --browser
fi
printf 'Ready: %s. Use one writer per task branch/worktree.\n' "$workspace"
