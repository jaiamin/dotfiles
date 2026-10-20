#!/usr/bin/env bash
# Apply saved settings inside the isolated Linux workspace. No installations.
set -euo pipefail

if [[ $(uname -s) != Linux ]]; then
  echo 'Run this script inside the Linux workspace, not on your Mac.' >&2
  exit 1
fi

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
backup_dir=''
staging=$(mktemp -d)
trap 'rm -rf -- "$staging"' EXIT

# Generate from the originals every time so the supplement never duplicates.
cat "$repo/dot_codex/AGENTS.md" > "$staging/AGENTS.md"
printf '\n' >> "$staging/AGENTS.md"
cat "$repo/sandbox/environment.md" >> "$staging/AGENTS.md"

backup() {
  local target=$1 relative=${1#"$HOME/"}
  if [[ -e "$target" || -L "$target" ]]; then
    if [[ -d "$target" && ! -L "$target" ]]; then
      echo "Expected a file, found a directory: $target" >&2
      exit 1
    fi
    if [[ -z "$backup_dir" ]]; then
      mkdir -p "$HOME/.local/state/dotfiles/backups"
      backup_dir=$(mktemp -d "$HOME/.local/state/dotfiles/backups/apply-XXXXXXXX")
    fi
    mkdir -p "$(dirname -- "$backup_dir/$relative")"
    cp -a -- "$target" "$backup_dir/$relative"
  fi
}

copy_config() {
  local source=$1 target=$2
  if [[ ! -L "$target" ]] && cmp -s -- "$source" "$target"; then
    return
  fi
  backup "$target"
  mkdir -p "$(dirname -- "$target")"
  # Replace a destination symlink rather than writing through it.
  cp --remove-destination -- "$source" "$target"
  chmod 600 "$target"
}

link_config() {
  local link_target=$1 target=$2
  if [[ -L "$target" && $(readlink -- "$target") == "$link_target" ]]; then
    return
  fi
  backup "$target"
  mkdir -p "$(dirname -- "$target")"
  ln -sfn -- "$link_target" "$target"
}

copy_config "$repo/sandbox/claude-settings.json" "$HOME/.claude/settings.json"
copy_config "$repo/sandbox/codex-config.toml" "$HOME/.codex/config.toml"
copy_config "$repo/sandbox/codex.rules" "$HOME/.codex/rules/default.rules"
copy_config "$repo/sandbox/opencode.json" "$HOME/.config/opencode/opencode.json"
copy_config "$staging/AGENTS.md" "$HOME/.codex/AGENTS.md"
copy_config "$repo/dot_gitconfig" "$HOME/.gitconfig"
copy_config "$repo/dot_config/git/ignore" "$HOME/.config/git/ignore"
link_config '../.codex/AGENTS.md' "$HOME/.claude/CLAUDE.md"
link_config '../../.codex/AGENTS.md' "$HOME/.config/opencode/AGENTS.md"
mkdir -p "$HOME/projects"

echo 'Linux configuration applied. Restart existing agent sessions.'
if [[ -n "$backup_dir" ]]; then
  printf 'Previous files saved in %s\n' "$backup_dir"
fi
