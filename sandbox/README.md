# Docker Sandboxes

One persistent, mountless sandbox per active project and primary agent. Add another agent sandbox only when needed. Project files and dependencies stay in Linux. Requires current `sbx` with mountless creation support (0.42+).

## Once per Mac

```sh
sbx login
sbx policy init balanced
sbx settings set ssh.agentForwardingEnabled false
sbx settings set skills.defaultMode readonly
sbx daemon restart
sbx setup ssh
sbx secret set github --command 'gh auth token'
sbx secret set openai --oauth
sbx skills import --dry-run
sbx skills import
```

Skip `policy init` if already initialized; inspect `sbx policy ls --wide` instead. Balanced allows common development destinations and asks about unfamiliar ones. It does not promise zero network prompts.

The GitHub command delegates your Mac GitHub CLI credential's permissions. Use repository-limited credentials when needed; keep production credentials out. Codex uses the host OAuth flow above. Claude subscription users use `/login` on first launch; do not add an Anthropic API key unless you want API billing. OpenCode needs its own supported provider configuration; do not assume it inherits Claude or ChatGPT subscriptions.

## Create a project environment

On the Mac, create ONE of these as needed. Do not add a workspace path or `.`:

```sh
sbx create --name bignums-claude --cpus 4 --memory 4g claude
# Alternatives, only when needed:
sbx create --name bignums-codex --cpus 4 --memory 4g codex
sbx create --name bignums-opencode --cpus 4 --memory 4g opencode
```

Four GiB is a starting limit; increase it for demanding builds, browsers, or databases. These are independent environments, not three required installations for every project.

Open the chosen sandbox from your Mac:

```sh
ssh bignums-claude.sbx
```

Inside Linux, clone dotfiles and bootstrap the project:

```sh
git clone https://github.com/jaiamin/dotfiles.git ~/.dotfiles
bash ~/.dotfiles/sandbox/bootstrap.sh jaiamin/bignums
exit
```

Before this branch is merged, add `--branch setup/docker-sandboxes` to the dotfiles clone command. Replace `jaiamin/bignums` with an existing repository. For a new project, create an empty GitHub repository first; do not initialize an unrelated checkout in the workspace before running bootstrap.

Bootstrap installs common Linux tools, instructions, Git identity, a portable Gitleaks hook, and the OpenCode overlay. Existing project hooks and Docker-managed agent configuration/authentication are preserved. Run it once in each new sandbox; never run chezmoi apply there.

## Work in Herdr

Run Herdr on the Mac. Use one workspace per project and run the matching command in a pane:

```sh
HERDR_AGENT=claude sbx run --name bignums-claude
HERDR_AGENT=codex sbx run --name bignums-codex
HERDR_AGENT=opencode sbx run --name bignums-opencode
```

Run only commands for sandboxes you created. These reopen existing sandboxes. Herdr's Local label refers to its Mac server, not where the agent executes. Agent status through wrappers is best effort. No Herdr server is required inside each sandbox.

Claude and Codex use Docker's default autonomous launch modes. OpenCode loads `sandbox/opencode.json` through the bootstrap's guest-only environment setting. Native Mac permissions stay supervised. Project settings can change agent behavior. Instructions to ask about consequential actions are behavioral rules, not an enforced approval gateway; credentials and repository protections remain important.

Use task branches/worktrees for concurrent workers. Separate mountless sandboxes have separate clones; exchange committed branches through GitHub. Start with one primary agent per project rather than creating a fleet.

## Browser and preview

Inside the chosen sandbox, only for UI projects:

```sh
bash ~/.dotfiles/sandbox/bootstrap.sh --browser
```

This installs agent-browser and Playwright Chromium, and explicitly sets the browser executable path for Linux ARM64. Start the dev server on `0.0.0.0`, for example with the project's `--host 0.0.0.0` option.

On the Mac:

```sh
sbx ports bignums-claude --publish 5173:5173
open http://localhost:5173
```

Use another host port for another project, such as `5174:5173`. Port publishing persists across restarts. SSH tunneling is optional, not needed for this workflow.

## Check and maintain

Before merging dotfiles, test one fresh sandbox: bootstrap, agent login, a real project test/build, and browser preview if applicable. Check Herdr's working/idle display, stop the sandbox, reopen it, and verify files and settings persisted.

Inside Linux, basic checks are:

```sh
cd /home/agent/workspace
git status --short
git config --global user.name
gh api user --jq .login
gitleaks version
```

For OpenCode, verify `opencode debug config` shows the intended permissions. For UI projects, run `agent-browser open https://example.com`, `agent-browser get title`, and `agent-browser close`.

To refresh instructions and the overlay inside an existing sandbox:

```sh
git -C ~/.dotfiles pull --ff-only
bash ~/.dotfiles/sandbox/bootstrap.sh jaiamin/bignums
```

After merging, a test clone on the setup branch should fetch and switch to main before future updates. Exit and relaunch the agent after refreshing settings. This does not pull the project or upgrade installed guest tools; update those separately. Docker template updates apply to new environments. Keep secret scanning in project CI and use project lockfiles.

On the Mac, inspect or approve a required destination:

```sh
sbx policy approval ls
sbx policy allow network --sandbox bignums-claude example.com:443
```

Routine lifecycle commands on the Mac:

```sh
sbx ls
sbx stop bignums-claude
# Only after preserving code, untracked files, and databases:
sbx rm bignums-claude
```

Files persist across stops, but processes end. Removing a sandbox deletes its internal data. A new Mac requires setup and cloning pushed projects; chezmoi does not back up VMs. Avoid blanket prune/reset commands for routine cleanup. Keep Mac directories and host Docker sockets unmounted; add host integrations only when needed.
