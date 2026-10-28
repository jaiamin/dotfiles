# dotfiles

Personal Apple Silicon Mac setup, with Orca and Docker Sandboxes for autonomous project work.
Your existing apps, Homebrew taps, shell/editor preferences, and skill catalog are preserved.
Projects, autonomous agents, dependencies, and browser automation run inside mountless Linux sandboxes.

## Install

Install Homebrew, then:

```sh
brew install chezmoi gh
env -u GH_TOKEN -u GITHUB_TOKEN gh auth login --hostname github.com --scopes workflow
chezmoi init --apply jaiamin
brew bundle --file="$(chezmoi source-path)/Brewfile"
```

Complete [sandbox setup and Orca connection](sandbox/README.md). Run `navi` for shortcuts.
Native agents remain available for supervised use; select a sandbox execution target for autonomous work.

## Update

```sh
chezmoi update
brew update
brew bundle --file="$(chezmoi source-path)/Brewfile"
sbx skills update
```

`git pull` updates source only; `chezmoi apply` deploys it. `chezmoi update` does both.
Review `chezmoi diff` before applying. Edit source preferences intentionally and preserve your existing Git workflow.
Portable native agent preferences remain tracked. Generated Orca hook commands, Codex hook approvals,
credentials, histories, and runtime databases do not belong in source control.

## Migrate an existing Mac

Back up local edits to the two retired paths in `.chezmoiremove` before the first apply.
The apply removes the old sandbox environment and Herdr config file, while preserving your other setup.
Run the full existing skill catalog into Docker with `bash "$(chezmoi source-path)/skills.sh"`.
Test a fresh project sandbox in Orca before retiring old task sandboxes or Herdr itself.

See the [Mac cleanup checklist](sandbox/README.md#mac-cleanup). Do not uninstall packages or remove skills
based on the earlier draft's broad cleanup suggestions; your used apps, taps, tools, and skills are retained.
