# dotfiles

Apple Silicon Mac clients with development inside mountless [Docker Sandboxes](sandbox/README.md).
Orca is the preferred UI; remote-capable editors and agent TUIs can use the same sandboxes.

## New Mac

Install Homebrew, then:

```sh
brew install chezmoi gh
env -u GH_TOKEN -u GITHUB_TOKEN gh auth login --hostname github.com --scopes workflow
chezmoi init --apply jaiamin
brew bundle --file="$(chezmoi source-path)/Brewfile"
code --install-extension ms-vscode-remote.remote-ssh
```

Complete the [sandbox setup](sandbox/README.md). Run `navi` for shortcuts.
Do not install project dependencies or coding-agent CLIs on the Mac.
Mac UI apps, shell/Git utilities, and Docker-managed images, credentials, and skills are intentional host state.
Neovim remains available as a native dotfiles editor; use it over SSH for project development.

## Update and edit

```sh
chezmoi update
brew update
brew bundle --file="$(chezmoi source-path)/Brewfile"
sbx skills update
```

Edit in `chezmoi source-path`, review `chezmoi diff`, then run `chezmoi apply`.
Commit and push source changes explicitly. Chezmoi runs only on the Mac.
Agent settings, hooks, approvals, credentials, and runtime databases are not managed here.

## Migration from the old task-sandbox setup

Existing sandboxes remain intact. Commit/push their work and preserve valuable ignored data before replacing them.
The new manager provisions project sandboxes; task branches/worktrees belong to Orca, another ADE, or ordinary Git.
Use the new Navi commands. The old `.sbxenv.yaml` and custom kit are retired.

Removing Brewfile entries does not uninstall existing packages. After validating the new workflow, uninstall
unused native `claude-code@latest`, `codex`, `opencode`, `agent-browser`, `ctx7`, `ast-grep`, `node`, `pnpm`, `prek`, and `uv`
where Homebrew dependencies allow. Do not run blanket Brewfile cleanup against personal applications.
Remove the obsolete `~/.sbxenv.yaml` after preserving any local edits: `sbx env` could otherwise still load it.

Existing host `~/.claude`, `~/.codex`, and OpenCode files also remain. Preserve credentials and conversation history.
Disable obsolete host agent hooks using their owning app; do not delete entire agent directories.
Generated Orca hooks and Codex approval hashes belong to the runtime that creates them, never back in this repo.
