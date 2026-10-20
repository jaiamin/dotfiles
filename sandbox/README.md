# OrbStack setup

Autonomous development runs here. Keep projects in `~/projects`.

## 1. Create | Mac

```sh
orb create --isolated --isolate-network ubuntu:noble agents
orb -m agents
```

Disable **Expose ports to LAN** in OrbStack. Keep Mac mounts and credential forwarding disabled.

## 2. Install | Linux

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

## 3. Configure | Linux

```sh
bash ~/dotfiles/sandbox/apply.sh
bash ~/dotfiles/skills.sh
gh auth login
```

Launch Claude, Codex, and OpenCode to sign in.

`apply.sh` installs saved settings and instruction links, backs up replaced files, and creates `~/projects`. Do not apply the Mac chezmoi configuration here.

## 4. Check | Linux

```sh
cd ~/dotfiles
git config --global user.name
git config --global user.email
git hook list pre-commit
agent-browser open https://example.com
agent-browser get title
agent-browser close
```

Expect your Git identity, a `gitleaks` hook, and `Example Domain`.

## 5. Connect | Mac

```sh
herdr machine add agents@orb
```

## Update | Linux

```sh
cd ~/dotfiles
git pull --ff-only
bash sandbox/apply.sh
brew update
brew bundle --file="$HOME/dotfiles/Brewfile.linux"
```

Restart agents after applying settings. Rerun `skills.sh` when updating skills; update standalone agents through their own updater.

Edit saved settings in `~/dotfiles`, then rerun `apply.sh`. Install project dependencies locally with `uv` or the project's JS package manager.

For rebuild testing, substitute `agents-test` in the Mac commands. Verify a small project before deleting the old machine, and preserve any unpushed work.
