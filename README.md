# dotfiles

Apple Silicon Mac preferences and T3 Code over SSH to mountless Docker Sandboxes.
Code, agents, dependencies, and task worktrees stay inside each project sandbox.

## Install

```sh
brew install chezmoi gh
env -u GH_TOKEN -u GITHUB_TOKEN gh auth login --hostname github.com --scopes workflow
chezmoi init --apply jaiamin
brew bundle --file="$(chezmoi source-path)/Brewfile"
```

Follow [sandbox setup](sandbox/README.md). Press **Ctrl+G** in Zsh and search `sandbox`
for project setup, agent updates, ports, and network access.

## Update

```sh
git -C "$(chezmoi source-path)" pull --ff-only
chezmoi diff
chezmoi apply
brew bundle --file="$(chezmoi source-path)/Brewfile"
```

Review `chezmoi diff` before applying, including any removals from `.chezmoiremove`.
Use **Refresh sandbox agents and tools** in Navi to update an existing sandbox.
