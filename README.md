# dotfiles

Two environments, one repository:

- **Mac:** hands-on coding, notebooks, learning, and agents with interactive permissions. Managed by chezmoi.
- **OrbStack:** autonomous development in an isolated Linux machine. Follow [the Linux setup](sandbox/README.md).

## New Mac

These instructions assume Apple Silicon. Install [Homebrew](https://brew.sh), then:

```sh
brew install chezmoi gh
gh auth login --hostname github.com --git-protocol https
chezmoi init --apply jaiamin
brew bundle --file="$(chezmoi source-path)/Brewfile"
```

Open a new terminal, then:

```sh
agent-browser install
bash "$(chezmoi source-path)/skills.sh"
```

Launch `claude`, `codex`, and `opencode` once to sign in. Sign into desktop apps as needed.

## Updates

```sh
chezmoi update
brew update
brew bundle --file="$(chezmoi source-path)/Brewfile"
```

Rerun `skills.sh` when changing or updating skills. Homebrew manages the apps and tools listed in `Brewfile`.

To edit tracked configuration, work in `$(chezmoi source-path)`, inspect `chezmoi diff`, then run `chezmoi apply`. Review and commit/push changes deliberately. If you edited a deployed file instead, use `chezmoi re-add <path>` first. Chezmoi currently auto-commits and auto-pushes changes made through its commands.

## Where things live

- `Brewfile`: Mac apps and tools. `Brewfile.linux`: shared Linux CLI tools.
- `dot_*`: Mac configuration. `dot_codex/AGENTS.md`: shared agent instructions.
- `skills.sh`: global skills for all three agents.
- `sandbox/`: Linux overrides, apply script, and rebuild instructions.

Chezmoi creates the Mac instruction symlinks. Linux uses the apply script instead of `chezmoi apply`. Logins and secrets stay outside this repository.
