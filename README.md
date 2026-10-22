# dotfiles

Personal setup for an Apple Silicon Mac. Native agents are supervised; [Docker Sandboxes](sandbox/README.md) handle autonomous work.

## New Mac

Install [Homebrew](https://brew.sh), then:

```sh
brew install chezmoi gh
env -u GH_TOKEN -u GITHUB_TOKEN gh auth login --hostname github.com --scopes workflow
chezmoi init --apply jaiamin
brew bundle --file="$(chezmoi source-path)/Brewfile"
```

Open a new terminal:

```sh
agent-browser install
code --install-extension ms-vscode-remote.remote-ssh
bash "$(chezmoi source-path)/skills.sh"
```

Sign in to your agents, then complete the [sandbox setup](sandbox/README.md). Run `navi` for command shortcuts.

## Update

```sh
chezmoi update
brew update
brew bundle --file="$(chezmoi source-path)/Brewfile"
```

To update skills, rerun `skills.sh` as above, then `sbx skills import` after sandbox setup.

## Edit

Edit files in `chezmoi source-path`, review `chezmoi diff`, then run `chezmoi apply`. Commit and push source changes.

Run chezmoi only on the Mac. Credentials and sandbox data are not synced. The sandbox recipe assumes the default chezmoi source path.
