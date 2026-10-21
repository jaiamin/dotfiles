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

Launch native agents to sign in. Complete the separate [sandbox setup](sandbox/README.md) once per Mac. Credentials and sandbox files are not synced by chezmoi.

## Update

```sh
chezmoi update
brew update
brew bundle --file="$(chezmoi source-path)/Brewfile"
```

Rerun `skills.sh` when updating skills, then `sbx skills import`. Update existing sandboxes separately using the sandbox README; reopening does not update their tools, instructions, or projects.

## Edit

Edit in `chezmoi source-path`, review `chezmoi diff`, then `chezmoi apply`. Commit and push changes.

- `Brewfile`: Mac apps and tools.
- `dot_codex/AGENTS.md`: shared agent instructions.
- `sandbox/`: guest bootstrap, OpenCode overlay, and instructions.
- `skills.sh`: shared skills.

Mac configuration assumes Apple Silicon. Keep credentials out of Git. Run chezmoi only on the Mac; sandbox setup uses its own small bootstrap.
