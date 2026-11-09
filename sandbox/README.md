# T3 Code + Docker Sandboxes

One mountless sandbox per project; one task branch/worktree per writer.
T3's UI runs on the Mac. Its server, agents, checkout, builds, and dependencies run in Linux.
Requires Docker Sandboxes 0.51.0+, T3 Code, and a Debian/Ubuntu agent template.
Bootstrap installs guest-local Node.js 24 LTS/npm when Node 22+ and working npm/npx are unavailable.

## One-time setup

```sh
sbx login
sbx settings set ssh.agentForwardingEnabled false
sbx settings set skills.defaultMode readonly
sbx daemon restart # finish active work first
sbx setup ssh
sbx secret set github --command 'env -u GH_TOKEN -u GITHUB_TOKEN gh auth token --hostname github.com'
bash "$(chezmoi source-path)/skills.sh"
```

On fresh installs only: `sbx policy init balanced`.
For Codex: `sbx secret set openai --oauth`. For Claude: sign in inside the sandbox using
[Docker's provider guide](https://docs.docker.com/ai/sandboxes/agents/claude-code/).
Keep coding-agent authentication Docker-managed; never copy host agent homes or OAuth tokens.

## Create and connect

From the dotfiles source directory, or use Navi:

```sh
bash sandbox/manage.sh create my-project owner/repo claude true
bash sandbox/manage.sh check my-project
# Existing managed sandbox, preserving its checkout and history:
bash sandbox/manage.sh refresh my-project owner/repo true
```

The repo needs an initial commit. Defaults: 4 CPUs, 4 GiB, read-only shared skills,
and the v3 `docker.io/sbx/t3code:latest` kit with telemetry off. `true` adds agent-browser/Chromium.
Additional kits must also be v3; legacy v1/v2 kits cannot be mixed with built-in agents.
Use `codex` or `opencode` instead of `claude`; append `-- --memory 8g` to change resources.

In T3: **Settings → Environments → Add environment → SSH**, host `my-project.sbx`.
Docker supplies the SSH user; no identity file is needed. Add a project on that environment
at **/home/agent/workspace**. In **Settings → Providers**, select that environment,
enable the installed provider, and verify login. T3 manages its server and SSH tunnel.

## Project API keys

In Navi, use **Set project API key** and **Remove project API key** as usual.
Only `api.openai.com` + `OPENAI_API_KEY` uses the temporary [OpenAI helper](openai-key.sh).
It prompts privately inside the VM and saves the real app key in
`/home/agent/.config/dotfiles/openai-api.sh`, owned by `agent` with mode `0600`.
The persistent shell sources that file and appends only `api.openai.com` to both
`NO_PROXY` and `no_proxy`, preserving other exclusions. SDKs that honor these
variables use transparent egress; Docker still enforces network policy.
The app key is readable inside the VM, never stored in this repository or Docker's host secret store.
The helper adopts the earlier manual setup and never edits agent auth/config files.

Create a Codex sandbox, set the project key in Navi, then connect T3. For an existing
connection, finish active work, quit T3 to stop SSH reconnection, stop/start the sandbox,
then reopen T3. Already-running processes retain their old environment after set/remove.
Codex OAuth stays on `chatgpt.com` through the forward proxy; app calls use
`api.openai.com` through transparent egress. This combination was live-verified in `ass`.

Other keys retain Docker's existing custom-secret flow. **Claude OAuth + an Anthropic
app key is not covered:** both target `api.anthropic.com`. A global proxy exclusion
would also bypass Claude's OAuth substitution; do not add one. See
[Docker issue #793](https://github.com/docker/sbx-releases/issues/793). That case needs
app-process-only credential/proxy settings and separate live verification.

When Docker fixes overlapping credentials, run the helper's `remove` action in each
configured sandbox (or use Navi), restart its processes, then delete only
`sandbox/openai-key.sh` from the source checkout. Navi falls back to Docker's original
custom-secret flow automatically; set the key there again. Removing the helper file
alone does not clean existing sandboxes. The helper leaves pre-existing Docker custom
secrets and independently configured proxy exclusions untouched; manage old custom
secrets with `sbx secret rm --sandbox NAME --host api.openai.com --env-name OPENAI_API_KEY`.

## Autonomous work

- Choose the remote project, **New worktree**, and **Full access** for each task.
  Set project defaults under **Settings → Threads → New threads → Permissions**.
- Give a concrete goal and verification command. Guest instructions allow task-branch commits,
  pushes, and a draft PR; merging and boundary/credential changes require approval.
- Use one active writer per worktree and separate dependencies, databases, and service ports.
  Worktrees share the VM; use another sandbox for stronger isolation.
- Keep long sessions running with `sbx run --detach --name my-project`.
  Stop after work finishes with `sbx stop my-project`. Mac sleep interrupts availability.

Full access reduces approval prompts; provider policies can still ask or reject commands.
Docker enforces isolation. Agent instructions do not enforce GitHub merge permissions.

## Maintenance and checks

`refresh` repairs Node/npm, installs missing T3 tooling, and updates instructions without changing branches,
dirty files, hooks, or auth. It does not upgrade installed T3/provider binaries.
Update skills with `sbx skills update`; update T3 and providers between sessions.
T3's built-in browser is separate from agent-browser and may need additional guest setup.

`check` verifies non-interactive SSH, Node/npm, T3, a committed checkout with an origin remote, instructions, and provider
CLI discovery. Also test login, skills, GitHub push, a build, two worktrees, and restart/reconnect
in T3 before merging. CI covers provisioning, Git, chezmoi, syntax, and secrets, not live providers.

Reuse existing managed sandboxes through `refresh`. Finish previous sessions first; preserve
uncommitted/ignored work. Previous IDE history is not imported. Uninstall old apps and review
guest packages, hooks, and published ports separately. Never delete whole agent homes or use
`sbx reset` for this migration. T3 runtime, credentials, and histories stay out of source control.

[Docker connection](https://docs.docker.com/ai/sandboxes/integrations/t3-code/) ·
[T3 permissions](https://github.com/pingdotgg/t3code/blob/main/docs/user/permission-modes.md) ·
[T3 updates](https://github.com/pingdotgg/t3code/blob/main/docs/user/updating.md)
