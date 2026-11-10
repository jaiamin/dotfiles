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

## Mobile access with Tailscale

Keep Tailscale on the Mac and phone, signed into the same account.
Route: phone → Mac Tailscale HTTPS → SSH → sandbox T3. This avoids the
Cloudflare tunnel DNS failure observed inside Docker Sandboxes.

1. Connect the sandbox in T3 desktop over SSH so its server is running.
2. On the **Mac**, keep this forward running in its own terminal:
   ```sh
   ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -L 127.0.0.1:44774:127.0.0.1:3773 my-project.sbx
   ```
3. In another Mac terminal, configure its private HTTPS endpoint once:
   ```sh
   tailscale serve --bg --https=8444 http://127.0.0.1:44774
   ```
4. Test `<printed-HTTPS-address>/.well-known/t3/environment` in phone Safari.
   Inside the **sandbox**, generate a fresh pairing code:
   ```sh
   npx t3 pair --base-dir /home/agent/.t3
   ```
5. In the phone app, add the **printed Tailscale HTTPS address, including its port**,
   and the **pairing code** (token after `#token=`). Ignore the local pairing URL/QR.

Pair once per sandbox, not per chat. Give each sandbox unique Mac/HTTPS ports. Check `ss -ltnp` if needed.
Keep both Tailscale clients connected, the Mac awake, and the sandbox running.
Serve persists across reboots; SSH forwards do not. After reboot, reconnect T3 desktop
and rerun each forward. No guest DNS edits or T3 restart are needed for this setup.

[T3 pairing](https://github.com/pingdotgg/t3code/blob/main/docs/user/remote-access.md) ·
[Tailscale Serve](https://tailscale.com/docs/reference/tailscale-cli/serve)

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
