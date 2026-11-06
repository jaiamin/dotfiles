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

Follow [sandbox setup](sandbox/README.md). In `navi`, search `sandbox` for daily commands.
Native agent settings remain available for supervised Mac work.

## Update

```sh
chezmoi update
brew update
brew bundle --file="$(chezmoi source-path)/Brewfile"
sbx skills update
```

Review `chezmoi diff` before applying. `git pull` updates source; `chezmoi apply` deploys it.
Existing sandboxes use `manage.sh refresh`; installed T3/provider binaries update separately.
Back up edits to paths in `.chezmoiremove`. App removal and existing runtime cleanup are manual.
