1. Create the machine from the Mac.
```
orb create --isolated --isolate-network ubuntu:noble agents
```
2. Disable Expose ports to LAN in OrbStack.
3. Enter Linux:
```
orb -m agents
```
4. Install Linux Homebrew prerequisites and Homebrew:
```
sudo apt-get update
sudo apt-get install -y build-essential procps curl file git unzip

NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

echo 'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"' >> ~/.bashrc
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
```
5. Clone dotfiles and install Linux packages:
```
git clone https://github.com/jaiamin/dotfiles.git ~/dotfiles
brew bundle --file=~/dotfiles/Brewfile.linux
```
6. Install the standalone agents:
```
curl -fsSL https://claude.ai/install.sh | bash
curl -fsSL https://chatgpt.com/codex/install.sh | sh
curl -fsSL https://opencode.ai/install | bash
source ~/.bashrc
```
7. Install the browser:
```
npx --yes playwright install --with-deps chromium
```
8. Apply the sandbox configuration
9. Connect Herdr from the Mac:
```
herdr machine add agents@orb
```
