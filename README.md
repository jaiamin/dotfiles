# dotfiles

- **Mac:** learning, notebooks, and hands-on development.
- **OrbStack:** autonomous agent development. See [setup](sandbox/README.md).

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

Launch Claude, Codex, and OpenCode to sign in.

## Update

```sh
chezmoi update
brew update
brew bundle --file="$(chezmoi source-path)/Brewfile"
```

Rerun `skills.sh` when updating skills.

## Edit

Edit files in `chezmoi source-path`, then run `chezmoi diff` and `chezmoi apply`. Commit and push changes.

- `Brewfile`: Mac apps and tools.
- `Brewfile.linux`: Linux tools.
- `dot_codex/AGENTS.md`: shared agent instructions.
- `sandbox/`: Linux settings and setup.
- `skills.sh`: shared skills.

Mac configuration assumes Apple Silicon. Keep credentials out of Git.
