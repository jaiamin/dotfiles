# dotfiles

- **Mac:** supervised development, learning, and notebooks.
- **Docker Sandboxes:** autonomous projects. See [setup](sandbox/README.md).

## New Mac

Install [Homebrew](https://brew.sh), then:

```sh
brew install chezmoi gh
gh auth login
chezmoi init --apply jaiamin
brew bundle --file="$(chezmoi source-path)/Brewfile"
```

Open a new terminal:

```sh
agent-browser install
bash "$(chezmoi source-path)/skills.sh"
```

Launch the native agents to sign in. Complete the separate [sandbox setup](sandbox/README.md) once per Mac. Docker credentials and existing sandbox files are not synced by chezmoi.

## Update

```sh
chezmoi update
brew update
brew bundle --file="$(chezmoi source-path)/Brewfile"
```

Rerun `skills.sh` when updating skills, then `sbx skills import` for sandboxes. Reopening with `dev` refreshes shared instructions; it does not pull project changes or upgrade installed guest tools automatically.

## Edit

Edit in `chezmoi source-path`, review `chezmoi diff`, then `chezmoi apply`. Commit and push changes.

- `Brewfile`: Mac apps and tools.
- `dot_codex/AGENTS.md`: shared agent instructions.
- `dot_local/bin/executable_dev`: Mac sandbox launcher.
- `sandbox/`: guest setup and instructions.
- `skills.sh`: shared skills.

Mac configuration assumes Apple Silicon. Keep credentials out of Git.
