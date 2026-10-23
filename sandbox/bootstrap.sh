#!/usr/bin/env bash
# Guest-only setup. Never replaces Docker-managed agent settings or auth files.
set -euo pipefail
if [[ $(uname -s) != Linux || $HOME != /home/agent ]]; then
  echo 'Run this inside a Docker Sandbox as agent, never on your Mac.' >&2; exit 1
fi
export PATH="$HOME/.local/bin:$PATH"
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
state_dir="$HOME/.local/state/dotfiles"
mkdir -p "$state_dir" "$HOME/.local/bin"

if [[ ${1:-} == --browser ]]; then
  command -v agent-browser >/dev/null || npm install --global --prefix "$HOME/.local" agent-browser
  # Playwright supplies Linux ARM64 builds. Do not rely on auto-discovery.
  npx --yes playwright install --with-deps chromium
  browser_path=$(find "$HOME/.cache/ms-playwright" -type f -path '*/chrome-linux*/chrome' -print -quit)
  [[ -n $browser_path && -x $browser_path ]] || { echo 'Chromium binary not found.' >&2; exit 1; }
  mkdir -p "$HOME/.agent-browser"
  # Preserve any other agent-browser settings.
  config="$HOME/.agent-browser/config.json"
  tmp=$(mktemp)
  trap 'rm -f -- "$tmp"' EXIT
  if [[ -f $config ]]; then
    jq --arg path "$browser_path" '.executablePath = $path' "$config" > "$tmp"
  else
    jq -n --arg path "$browser_path" '{executablePath: $path}' > "$tmp"
  fi
  install -m 600 "$tmp" "$config"
  agent-browser open about:blank
  agent-browser close
  exit 0
fi

repo=${1:?Pass OWNER/REPO}
[[ $repo =~ ^[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+$ && $repo != */. && $repo != */.. ]] || exit 1
if [[ ! -f $state_dir/tools-v1 ]]; then
  sudo apt-get update
  sudo apt-get install -y build-essential ca-certificates curl git git-lfs gh jq ripgrep unzip shellcheck
  if ! command -v node >/dev/null || ! command -v npm >/dev/null; then
    echo 'Expected Node/npm in the Docker agent template.' >&2; exit 1
  fi
  command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
  command -v pnpm >/dev/null || npm install --global --prefix "$HOME/.local" pnpm
  if ! command -v gitleaks >/dev/null; then
    version=8.30.1
    case $(uname -m) in aarch64|arm64) arch=arm64 ;; x86_64) arch=x64 ;; *) echo 'Unsupported Gitleaks architecture.' >&2; exit 1 ;; esac
    archive="gitleaks_${version}_linux_${arch}.tar.gz"
    tmp_dir=$(mktemp -d)
    trap 'rm -rf -- "$tmp_dir"' EXIT
    base="https://github.com/gitleaks/gitleaks/releases/download/v$version"
    curl -fsSL "$base/$archive" -o "$tmp_dir/$archive"
    curl -fsSL "$base/gitleaks_${version}_checksums.txt" -o "$tmp_dir/checksums.txt"
    (cd "$tmp_dir"; awk -v file="$archive" '$2 == file { print; found=1 } END { if (!found) exit 1 }' checksums.txt > selected-checksum; sha256sum -c selected-checksum)
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

# Install the latest selected agent before continuing.
agent=${DOTFILES_AGENT:?Missing DOTFILES_AGENT}

case "$agent" in
  codex)
    npm install -g --prefix "$HOME/.local" \
      --include=optional @openai/codex@latest
    ;;
  claude)
    curl -fsSL https://claude.ai/install.sh | bash -s -- latest
    ;;
  opencode)
    npm install -g --prefix "$HOME/.local" \
      --include=optional opencode-ai@latest
    ;;
  *)
    echo "Unsupported agent: $agent" >&2
    exit 1
    ;;
esac

hash -r
command -v "$agent"
"$agent" --version

# One generated instruction file, shared by all supported agent locations.
mkdir -p "$HOME/.config/dotfiles" "$HOME/.claude" "$HOME/.codex" "$HOME/.config/opencode" "$HOME/.config/git"
cat "$source_dir/dot_codex/AGENTS.md" "$source_dir/sandbox/environment.md" > "$HOME/.config/dotfiles/AGENTS.md"
ln -sfn ../.config/dotfiles/AGENTS.md "$HOME/.claude/CLAUDE.md"
ln -sfn ../.config/dotfiles/AGENTS.md "$HOME/.codex/AGENTS.md"
ln -sfn ../dotfiles/AGENTS.md "$HOME/.config/opencode/AGENTS.md"
# Load a separate OpenCode overlay without replacing Docker-managed config/auth.
install -m 600 "$source_dir/sandbox/opencode.json" "$HOME/.config/dotfiles/opencode.json"
# Expand HOME when each guest session starts, not while generating the file.
# shellcheck disable=SC2016
opencode_line='export OPENCODE_CONFIG="$HOME/.config/dotfiles/opencode.json"'
if ! sudo grep -Fxq -- "$opencode_line" /etc/sandbox-persistent.sh 2>/dev/null; then
  printf '\n%s\n' "$opencode_line" | sudo tee -a /etc/sandbox-persistent.sh >/dev/null
fi
install -m 644 "$source_dir/dot_config/git/ignore" "$HOME/.config/git/ignore"
git config --global user.name "$(git config --file "$source_dir/dot_gitconfig" user.name)"
git config --global user.email "$(git config --file "$source_dir/dot_gitconfig" user.email)"
git config --global init.defaultBranch main
git config --global push.autoSetupRemote true
git config --global fetch.prune true
git config --global core.excludesFile "$HOME/.config/git/ignore"

workspace=/home/agent/workspace
if [[ ! -d $workspace/.git ]]; then
  # Git refuses a nonempty destination. Never overwrite or clean it automatically.
  git -c 'credential.helper=!gh auth git-credential' clone "https://github.com/$repo.git" "$workspace"
fi
origin=$(git -C "$workspace" remote get-url origin)
[[ $origin == "https://github.com/$repo.git" || $origin == "https://github.com/$repo" ]] || {
  echo 'Existing checkout belongs to another repository; leaving it untouched.' >&2; exit 1;
}
# Scope the HTTPS helper to this checkout, without replacing global auth settings.
git -C "$workspace" config credential.https://github.com.helper '!gh auth git-credential'
# Portable Git hook; preserve repository-installed hooks and custom hook managers.
hook="$workspace/.git/hooks/pre-commit"
if [[ -z $(git -C "$workspace" config --get core.hooksPath || true) && ! -e $hook && ! -L $hook ]]; then
  mkdir -p "$(dirname "$hook")"
  cat > "$hook" <<'HOOK'
#!/usr/bin/env bash
export PATH="$HOME/.local/bin:$PATH"
exec gitleaks git --pre-commit --staged --redact --no-banner
HOOK
  chmod 755 "$hook"
fi

# Assign the sandbox to one task branch.
# Reuse the saved assignment when refreshing an older session.
assigned=$(git -C "$workspace" config --local --get sandbox.assignedBranch || true)
branch=""

if [[ -n ${DOTFILES_TASK:-} ]]; then
  selection=${DOTFILES_BRANCH:-new}
  if [[ $selection == new ]]; then
    branch="agent/$DOTFILES_TASK"
  else
    branch=$selection
  fi
elif [[ -n $assigned ]]; then
  branch=$assigned
  selection=existing
else
  echo 'No task specified and no saved branch assignment.' >&2
  exit 1
fi

if [[ -n $branch ]]; then
  git -C "$workspace" check-ref-format --branch "$branch" >/dev/null

  if [[ $branch == main || $branch == master ]]; then
    echo 'Cannot assign the default branch.' >&2
    exit 1
  fi

  if [[ -n $assigned && $assigned != "$branch" ]]; then
    echo "Sandbox already assigned to $assigned" >&2
    exit 1
  fi

  current=$(git -C "$workspace" branch --show-current)

  if [[ $current != "$branch" ]]; then
    if [[ -n $assigned || -n $(git -C "$workspace" status --porcelain) ]]; then
      echo 'Refusing to switch an assigned or modified checkout.' >&2
      exit 1
    fi

    git -C "$workspace" fetch --prune origin

    base=$(git -C "$workspace" symbolic-ref --quiet --short refs/remotes/origin/HEAD)
    base=${base#origin/}

    if [[ $current != "$base" ]]; then
      echo "Expected a fresh checkout of $base, got $current" >&2
      exit 1
    fi

    if [[ $selection == new ]]; then
      if git -C "$workspace" show-ref --verify --quiet "refs/remotes/origin/$branch" ||
         git -C "$workspace" show-ref --verify --quiet "refs/heads/$branch"; then
        echo "Task branch already exists: $branch" >&2
        exit 1
      fi

      git -C "$workspace" switch --no-track -c "$branch" "origin/$base"
    else
      if ! git -C "$workspace" show-ref --verify --quiet "refs/remotes/origin/$branch"; then
        echo "Remote branch not found: $branch" >&2
        exit 1
      fi

      git -C "$workspace" switch --track -c "$branch" "origin/$branch"
    fi
  fi

  git -C "$workspace" config --local sandbox.assignedBranch "$branch"
  git -C "$workspace" config --local pull.ff only
  
  printf '\n## Assigned task\n- Branch: %s\n- Stay on this branch. Read HANDOFF.md if present.\n' \
    "$branch" >> "$HOME/.config/dotfiles/AGENTS.md"

fi

printf 'Ready: %s. Existing project hooks are preserved; keep secret scanning in CI too.\n' "$workspace"
