# Docker Sandboxes

Persistent, mountless Linux environments for autonomous projects. Herdr stays on the Mac. Use one primary agent per project; create another environment only when useful.

Use current `sbx` (v0.49.1 recommended). Kits are Early Access; environment files and shared skills are experimental. No Docker Desktop, custom image, or host launcher is needed for this setup.

## Once per Mac

After the root README's Mac setup:

```sh
sbx login
sbx settings set ssh.agentForwardingEnabled false
sbx settings set skills.defaultMode readonly
sbx daemon restart
sbx setup ssh
sbx secret set github --command 'gh auth token'
sbx secret set openai --oauth
sbx skills import --dry-run
sbx skills import
```

On a fresh installation, run `sbx policy init balanced`. If policy already exists, inspect `sbx policy ls --wide` instead. Balanced permits common development services and asks about unfamiliar destinations. Keep `browser.enabled` at its default so subscription login can open your Mac browser. Clipboard image access remains off unless you choose to enable it.

The GitHub command delegates your Mac GitHub CLI credential's permissions; use a repository-limited credential for sensitive projects. Codex uses the host OAuth flow above. Claude subscription users use `/login` on first launch. Do not add an Anthropic API key unless you want API billing. OpenCode requires its own supported provider configuration; do not assume it inherits Claude or ChatGPT subscriptions.

## Create and work

Run on the Mac, in a local Herdr pane:

```sh
HERDR_AGENT=claude sbx env run ~/.sbxenv.yaml \
  --name bignums-claude --env-arg repo=jaiamin/bignums
```

Explicitly selecting the shared file avoids loading a project-supplied environment file. Omit `workspace` and `additionalWorkspaces` from this recipe; no Mac project directory is mounted. Approve the initial plan and legitimate credential requests. The shared v2 mixin installs tools, instructions, Git identity, a Gitleaks hook, and the OpenCode overlay, then clones the project. Docker applies this during creation; no manual SSH/bootstrap is required. The kit uses the dotfiles main branch for guest setup; pass `--env-arg ref=BRANCH` to test another published branch or tag.

For another agent, create only what you need:

```sh
HERDR_AGENT=codex sbx env run ~/.sbxenv.yaml \
  --name bignums-codex --env-arg agent=codex --env-arg repo=jaiamin/bignums
HERDR_AGENT=opencode sbx env run ~/.sbxenv.yaml \
  --name bignums-opencode --env-arg agent=opencode --env-arg repo=jaiamin/bignums
```

For UI projects, add `--env-arg browser=true` at creation. This installs agent-browser and Playwright Chromium and sets the executable path explicitly for Linux ARM64. Otherwise the agent can install browser support later inside Linux with `bash ~/.dotfiles/sandbox/bootstrap.sh --browser`.

The bootstrap expects an existing GitHub repository. Create an empty repository first for a new project. Four CPUs and 4 GiB are starting limits; adjust the recipe for demanding builds/browsers before creating the environment. Each environment has separate dependencies, caches, and project files. Do not change the recipe's repository/agent arguments to repurpose an existing sandbox name.

Reopen existing environments with short commands:

```sh
HERDR_AGENT=claude sbx run --name bignums-claude
HERDR_AGENT=codex sbx run --name bignums-codex
HERDR_AGENT=opencode sbx run --name bignums-opencode
```

Only reopen names you created. Bare `sbx run claude` creates a host-mounted workspace by default; use the shared recipe for new environments. Herdr's Local label refers to its Mac server, not the execution boundary. The hint helps screen-based status detection; it does not configure permissions. Use one Herdr workspace per project. No Herdr server is required inside the sandbox.

Claude/Codex retain Docker's autonomous launch defaults. OpenCode uses the guest overlay without replacing Docker-managed config/auth. Native Mac agents remain supervised. Instructions to ask about consequential actions are behavioral rules, not an enforced approval gateway. Keep credentials limited and production access out. Use task branches/worktrees for parallel workers; separate sandboxes exchange committed branches through GitHub.

## Preview and inspect

Ask the agent to run the dev server on `0.0.0.0`. On the Mac:

```sh
sbx ports bignums-claude --publish 5173:5173
open http://localhost:5173
ssh bignums-claude.sbx
```

Use another host port for another project, such as `5174:5173`. SSH/editor work happens in `/home/agent/workspace`. Port publication persists; the app process must still be running. If you need the sandbox to stay running after all sessions disconnect, `sbx run -d --name bignums-claude` enables detached mode. Detached mode persists until recreation. It still stops when you explicitly stop it or your Mac shuts down; resuming processes after reboot is separate from preserving files.

## Check and maintain

Before merging a setup change, create a fresh environment and check agent login, instructions, `git config --global user.name`, `gh api user --jq .login`, `gitleaks version`, a project test/build, and browser preview if needed. Check `opencode debug config` in an OpenCode environment. Stop and reopen to verify persistence.

On the Mac:

```sh
sbx ls
sbx policy approval ls
sbx policy log
sbx diagnose
```

Allow a needed destination narrowly, for example `sbx policy allow network --sandbox bignums-claude example.com:443`. Docker's `sbx` dashboard is also available for sandbox and network management.

After `chezmoi update`, rerun `skills.sh` and `sbx skills import` when updating skills. Existing guests do not automatically receive new dotfiles, tool versions, or kit definitions. To refresh guest instructions/configuration, inside Linux:

```sh
git -C ~/.dotfiles pull --ff-only
bash ~/.dotfiles/sandbox/bootstrap.sh jaiamin/bignums
```

Exit and relaunch the agent after config changes. Update project dependencies and installed guest tools separately. Changing the shared recipe's kits/resources/ports does not update an existing environment; use the relevant supported command or create a new named environment after preserving work. Do not assume `sbx kit add` is a general update command.

Routine lifecycle on the Mac:

```sh
sbx stop bignums-claude
# Only after preserving code, untracked files, and databases:
sbx rm bignums-claude
```

Stopping preserves files and ends processes. Removing deletes internal data. Push important work regularly; chezmoi does not back up VMs. Avoid blanket prune/reset. Saved templates are optional conveniences, not complete backups. Do not add broad host mounts, host Docker sockets, or host-executed MCP tools without a concrete need.
