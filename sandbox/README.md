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
Keep authentication Docker-managed; never copy host agent homes or real tokens.

Creating a `codex` sandbox selects the local OAuth-only Codex workload and the
separate project OpenAI API kit, alongside T3. Approve both credential bindings,
even if the project key is not set yet. Shared skills and MCP startup are retained.
The host `openai` secret remains OAuth; project API keys use `project-openai`.
See [credential routing and the isolated auth probe](kits/README.md).

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

In Navi, **Set project API key** with `api.openai.com` / `OPENAI_API_KEY` uses
the `project-openai` service for these new Codex sandboxes. The app reads the
public `proxy-managed` sentinel; Docker injects the real API key only at the API
host. Key rotation and removal never replace the global Codex OAuth credential.
Other hosts and legacy sandboxes retain the custom-secret flow, with normal
Navi suggestions and custom values. Start a new app process after adding a new
environment variable. Native OpenAI key rotations need no app restart.

The live-validated combination is Codex OAuth plus an OpenAI project API key.
Claude and OpenCode creation are unchanged. In particular, Claude OAuth plus a
separate Anthropic API key targets the same host and remains unverified; this
OpenAI routing fix is not a blanket fix for that case.

In T3: **Settings → Environments → Add environment → SSH**, host `my-project.sbx`.
Docker supplies the SSH user; no identity file is needed. Add a project on that environment
at **/home/agent/workspace**. In **Settings → Providers**, select that environment,
enable the installed provider, and verify login. T3 manages its server and SSH tunnel.

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

`refresh` and restarts do not replace a sandbox's creation-time credential kits.
Use a new sandbox for the separated OpenAI routing; preserve the old checkout
until its work has been transferred. After updating dotfiles with `chezmoi update`,
new Navi-created Codex sandboxes use this setup. No daemon or T3 restart is
required just to deploy these source files or rotate the project API key.

[Docker connection](https://docs.docker.com/ai/sandboxes/integrations/t3-code/) ·
[T3 permissions](https://github.com/pingdotgg/t3code/blob/main/docs/user/permission-modes.md) ·
[T3 updates](https://github.com/pingdotgg/t3code/blob/main/docs/user/updating.md)
