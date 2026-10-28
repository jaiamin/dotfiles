# Orca and Docker Sandboxes

Use one mountless sandbox per project and credential boundary, with task worktrees inside it.
Worktrees share a VM's processes, services, and accessible data; use another sandbox for stronger isolation.
Docker Sandboxes is standalone. It does not depend on Docker Desktop or host Node.
Your existing native tools and apps are kept; the sandbox workflow does not require removing them.

## Setup

```sh
sbx login
sbx settings set ssh.agentForwardingEnabled false
sbx settings set skills.defaultMode readonly
# Pause existing work before restarting the daemon.
sbx daemon restart
sbx setup ssh
sbx policy ls --wide
sbx secret set github --command 'env -u GH_TOKEN -u GITHUB_TOKEN gh auth token --hostname github.com'
sbx secret set openai --oauth
bash "$(chezmoi source-path)/skills.sh"
```

On a fresh installation only, initialize `sbx policy init balanced`.
Claude subscription users sign in with `/login` inside Claude. Other providers follow their Docker agent guide.
Credentials stay in Docker's host store; do not copy host agent homes or real tokens into Linux.

## Create and connect

Use Navi, or run from the dotfiles source directory:

```sh
bash sandbox/manage.sh create my-project owner/repo claude true
# Agent and resources can vary:
bash sandbox/manage.sh create my-codex owner/repo codex false -- --memory 8g
bash sandbox/manage.sh refresh my-project owner/repo true
```

The repository needs an initial commit. `true` adds Linux browser automation. Defaults: 4 CPUs, 4 GiB.
Any Docker-supported built-in agent or workload reference is accepted. Additional kits must match its v2/v3 format.
The shared bootstrap requires a Debian/Ubuntu image with Node/npm, as standard agent templates provide.
It prepares tools and a checkout; Docker owns agent installation, authentication, and managed configuration.
Refresh preserves branches, dirty files, and project hooks. It does not upgrade agent binaries.

In Orca: Settings → SSH → Add Target. Host `my-project.sbx`, user `_default_user_`, no identity file.
Test and save. Add the remote repository `/home/agent/workspace`, then create task worktrees with this host under **Run on**.
Only agents installed inside that sandbox appear in its picker. Use a compatible agent mixin or another sandbox for a second agent.

Let Orca own task worktrees. Use one writer per branch/worktree, separate dependencies and service ports, and a draft PR.
Portable guidance from `dot_codex/AGENTS.md` is combined with `sandbox/AGENTS.md` inside the guest.
Claude/Codex/OpenCode instruction locations are linked;
other agents retain their native kit behavior. Update agent binaries with their own guest-side updater between sessions.
Skills use Docker's managed read-only store. Agents outside that integration need in-sandbox skill setup.

## Optional full Orca runtime

Direct SSH supports remote worktrees, editing/diffs, Git, terminals, and agents. Some richer structured-chat
and conversation-continuation features need a paired Orca runtime rather than a plain SSH workspace.

```sh
bash sandbox/manage.sh orca my-project 6768
sbx exec my-project -- cat /home/agent/.local/state/dotfiles/orca/server.log
```

This installs the official Linux Orca package if absent, starts its server, and publishes a localhost port.
Paste the private pairing URL from the log into Settings → Remote Orca Servers → Add Server.
Select that runtime for its projects. Use another port for another sandbox; keep the pairing log private.
Client and server versions must be compatible. The adapter does not upgrade an installed server automatically.

This optional combination is beta and is not Docker's documented Orca SSH integration. Check the log for readiness.
Apple Silicon startup, provider auth, pairing, and chat continuation remain pre-merge runtime checks.
Stopping the sandbox stops its server; run the command again to restart it. A local VM pauses with Mac sleep.

## Mac cleanup

Preserve your existing apps, taps, native tools, editor/shell setup, and skills. This migration changes
sandbox plumbing and removes generated runtime snapshots; it is not a package or skill purge.

1. Back up local edits to `~/.sbxenv.yaml` and `~/.config/herdr/config.toml`; `.chezmoiremove` retires those exact files on apply.
2. Review `chezmoi diff`, then apply. Portable native Claude/Codex/OpenCode preferences remain; generated hook commands and approval hashes are excluded from source.
3. Run `bash "$(chezmoi source-path)/skills.sh"` to install your entire existing catalog directly into Docker's managed shared store.
4. Use `sbx skills ls` and `sbx skills update` for that store. Do not prune skills from the catalog.
5. Keep native `npx` skill directories if you use them with native agents. Docker installation does not delete or update those copies.
6. After the Orca sandbox works, quit Herdr and uninstall its package only if it is still installed and no longer used.
7. Retire old task sandboxes individually after pushing commits and preserving ignored files, databases, and other local data.

Do not delete whole agent homes, credentials, histories, native skill directories, or browser caches as part of this migration.
Do not use `sbx reset`: it deletes sandbox state and stored credentials. No blanket `brew bundle cleanup` is needed.
Orca manages its own generated hook scripts, pairing tokens, logs, and runtime databases locally; do not add them to dotfiles.

## Before merging

1. Run CI: shell/config checks, real Git regression tests, a temporary-home chezmoi apply, and secret scanning.
2. On the Mac, create a fresh sandbox and inspect its mounts. Test provider auth, GitHub push, skills, and a project build.
3. Create two worktrees in Orca, use separate ports, and confirm secret scanning in both.
4. If using the full runtime, verify server startup, pairing, structured chat, continuation, and reconnect.
5. Stop/restart the sandbox and verify persisted files before retiring the old setup.

CI cannot establish that the Mac/VM/provider checks passed. Keep this PR draft until those are verified.

Sources: [Docker Orca connection](https://docs.docker.com/ai/sandboxes/integrations/orca/),
[Docker usage](https://docs.docker.com/ai/sandboxes/usage/),
[skills](https://docs.docker.com/ai/sandboxes/workflows/agent-skills/),
[Orca chat](https://github.com/stablyai/orca/blob/main/docs/site/content/docs/agents/native-chat.mdx),
[Orca servers](https://github.com/stablyai/orca/blob/main/docs/site/content/docs/remote-servers.mdx).
