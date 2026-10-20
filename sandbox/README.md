# Isolated agent workspace

Run autonomous projects here; use the Mac for hands-on learning and small local work. Keep projects in Linux at `~/projects`. Do not enable Mac mounts, host integration, credential forwarding, or access to the Mac's Docker socket.

## 1. Create the machine | Mac

```sh
orb create --isolated --isolate-network ubuntu:noble agents
```

Disable **Expose ports to LAN** in OrbStack. Enter Linux:

```sh
orb -m agents
```

For a rebuild test, use `agents-test` instead of `agents` in the Mac commands. Keep the working machine until the test passes.

## 2. Install tools | Linux

```sh
sudo apt-get update
sudo apt-get install -y build-essential procps curl file git unzip
NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
echo 'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"' >> ~/.bashrc
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"

git clone https://github.com/jaiamin/dotfiles.git ~/dotfiles
brew bundle --file="$HOME/dotfiles/Brewfile.linux"

curl -fsSL https://claude.ai/install.sh | bash
curl -fsSL https://chatgpt.com/codex/install.sh | sh
curl -fsSL https://opencode.ai/install | bash
source ~/.bashrc

npx --yes playwright install --with-deps chromium
```

These are fresh-machine installation steps. Use the update section for an existing machine.

## 3. Apply settings and sign in | Linux

```sh
bash ~/dotfiles/sandbox/apply.sh
bash ~/dotfiles/skills.sh
gh auth login --hostname github.com --git-protocol https
```

Launch `claude`, `codex`, and `opencode` separately and complete sign-in. Follow their terminal instructions if browser login cannot open automatically. Never copy Mac credential folders into Linux.

The script installs Linux agent settings, Codex rules, Git settings/ignores, and shared instructions with the Linux supplement. It creates instruction symlinks and `~/projects`. Changed files are backed up under `~/.local/state/dotfiles/backups/`; credentials and projects are untouched. Do not run `chezmoi init --apply` here.

## 4. Verify | Linux

```sh
cd ~/dotfiles
uname -s
git config --global user.name
git config --global user.email
git hook list pre-commit
gh auth status
ls -l ~/.claude/CLAUDE.md ~/.config/opencode/AGENTS.md
agent-browser open https://example.com
agent-browser get title
agent-browser close
```

Expect Linux, your Git identity, a `gitleaks` hook, instruction symlinks, and `Example Domain`. If `git hook list` is unavailable, reopen the terminal and confirm `command -v git` points to Homebrew Git.

Start each agent in a project under `~/projects`. Confirm it loads the shared/Linux instructions and the expected permission mode. Have it make a small change, run tests, and start/test a local API before retiring the old machine. Automatic approval review may still pause on risky actions; instructions and command rules are guardrails, not guaranteed human approval gates.

## 5. Connect Herdr | Mac

```sh
herdr machine add agents@orb
```

Choose that machine for autonomous work. Confirm its terminal reports `Linux`.

## Updates | Linux

```sh
cd ~/dotfiles
git pull --ff-only
bash sandbox/apply.sh
brew update
brew bundle --file="$HOME/dotfiles/Brewfile.linux"
```

Rerun `bash ~/dotfiles/skills.sh` when updating skills. Update standalone agents with their own updater. Edit saved settings in this repository, then rerun `apply.sh`; it replaces the managed files rather than merging local changes. Restart agent sessions after applying settings.

Add project dependencies with `uv` or the project's JS package manager. Add shared CLI tools to `Brewfile.linux`. Install databases, Docker, and other infrastructure only when a project needs them. Before deleting any machine, push or back up its projects, unpushed commits, and other data you need.
