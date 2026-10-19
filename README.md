# dotfiles

## New Mac
1. Install Homebrew (brew.sh) and sign into the App Store.
2. `brew install chezmoi gh && gh auth login && chezmoi init --apply jaiamin`
3. `brew bundle`
4. `agent-browser install`
5. `ln -s ~/.codex/AGENTS.md ~/.claude/CLAUDE.md` (and similar for other agents)
6. `$(chezmoi source-path)/skills.sh`
