# dotfiles

Mac setup managed with chezmoi and Homebrew.

## New Mac
1. Install Homebrew (brew.sh) and sign into the App Store.
2. Apply dotfiles:
```sh
   brew install chezmoi gh && gh auth login && chezmoi init --apply jaiamin
```
3. Install apps and tools:
```sh
   brew bundle --file="$(chezmoi source-path)/Brewfile"
```
4. Install the browser for agents: `agent-browser install`
5. Install global agent skills: `"$(chezmoi source-path)/skills.sh"`
6. Open a new terminal.

AGENTS.md lives at `~/.codex/AGENTS.md`. chezmoi symlinks it to other agents (e.g. Claude Code, Opencode).
