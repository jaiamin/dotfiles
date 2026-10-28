# Sandboxed development

One persistent mountless sandbox per project and credential boundary; task worktrees live inside it.
Use a separate sandbox for risky experiments. Worktrees share the VM's files, processes, services, and credentials.

## Host setup

```sh
sbx login
sbx settings set ssh.agentForwardingEnabled false
sbx settings set skills.defaultMode readonly
# Restart only after pausing existing work; it can interrupt sandbox sessions.
sbx daemon restart
sbx setup ssh
sbx secret set github --command 'env -u GH_TOKEN -u GITHUB_TOKEN gh auth token --hostname github.com'
sbx secret set openai --oauth
bash "$(chezmoi source-path)/skills.sh"
```

For a fresh setup, initialize `sbx policy init balanced`. Otherwise inspect existing policy.
Claude subscription users use `/login` inside Claude. Other agents use Docker's documented provider authentication.
Keep proxy-managed credentials on the host. Do not copy host agent homes or real tokens into the VM.
Docker Sandboxes is standalone; Docker Desktop is not needed.

## Create and refresh

Use Navi or run from the dotfiles source directory:

```sh
bash sandbox/manage.sh create my-project owner/repo claude true
# Any Docker-supported built-in agent or workload kit reference is accepted.
bash sandbox/manage.sh create my-codex owner/repo codex false -- --memory 8g
bash sandbox/manage.sh refresh my-project owner/repo true
```

The repository needs an initial commit. Names use lowercase letters, digits, and hyphens, starting with a letter.
`true` installs browser automation inside Linux. Default resources are 4 CPUs and 4 GiB; tune for actual workloads.
Creation adds explicit package-download and Context7 domains to that sandbox only; other network policy stays intact.
Creation refuses existing names. Refresh is limited to manager-created sandboxes and refuses repository mismatches.
It preserves branches, dirty files, project hooks, and Docker-managed agent settings. It does not upgrade agents.

The manager calls `sbx create` with no workspace path, copies a small local setup payload with `sbx cp`, then
runs the guest bootstrap. No dotfiles push, custom kit, registry publication, or host Node runtime is needed.
Allowed forwarded flags: `--cpus`, `--memory`, `--template`, `--pull`, `--kit`, `--kit-arg`, `--kit-args-file`.
Do not introduce host mounts through additional kits. Review their declared capabilities first.
Docker enforces kit compatibility; v2 and v3 cannot be mixed. Bare built-in agent names currently select v2.

The common tool bootstrap targets Debian/Ubuntu images with Node/npm, as provided by standard agent templates.
Other images can be run with native `sbx` commands; adapt their package setup before applying this bootstrap.
The manager does not implement or replace agent installation, authentication, or permission systems.

Project path: `/home/agent/workspace`. Setup payload: `/home/agent/.config/dotfiles/source`.
Shared instructions are `sandbox/AGENTS.md`; common Claude/Codex/OpenCode instruction locations are linked.
Agents with other instruction conventions keep their native kit behavior; add an instruction adapter only if needed.
OpenCode has a separate optional settings overlay; its Docker-managed settings/auth files are preserved.

## Choose a UI or terminal

| Client | Connection | Execution |
| --- | --- | --- |
| Orca, documented SSH mode | Settings → SSH; `my-project.sbx`, `_default_user_`, no identity file | Remote worktrees, Git, terminals, and agents |
| Orca, optional full runtime | Paired Remote Orca Server below | Sandbox owns the Orca runtime and supported structured chats |
| VS Code / Cursor | Remote SSH to `my-project.sbx` | Remote workspace and development tools |
| T3 Code | Add SSH environment `my-project.sbx` | T3 server and agents in sandbox |
| ChatGPT / Claude Desktop | Their documented Docker SSH connection | Supported remote coding backend |
| Agent TUI | `sbx run --name my-project`, or SSH / `sbx exec -it -w PATH ...` | Agent inside sandbox |

Select the actual task worktree path in each client. One writer per branch/worktree across all clients.
For TUI-first work, create a task branch/worktree with ordinary Git before editing. Orca can discover external worktrees.
Orca's agent picker only sees installed agents. Use a compatible agent mixin or another sandbox for a second agent;
installing an arbitrary binary alone does not configure its credentials, MCP, or UI integration.
A desktop app without a remote execution backend cannot be made fully sandboxed by dotfiles alone.

## Optional full Orca runtime (beta integration)

The Docker-documented direct SSH route is useful for worktrees, editor/diffs, terminals, and agents.
It is not feature-equivalent to a paired Orca server: current Orca docs restrict structured-chat availability and
conversation-continuation actions by execution host. Direct SSH without an Orca runtime lacks those continuation actions.

To try a sandbox-owned runtime:

```sh
bash sandbox/manage.sh orca my-project 6768
sbx exec my-project -- cat /home/agent/.local/state/dotfiles/orca/server.log
```

The adapter downloads the official Linux Orca `.deb` for the sandbox architecture if it is not installed,
starts `orca-ide serve` under a lock, and publishes that port to the Mac's loopback interface.
Paste the private pairing URL from the log into Orca → Settings → Remote Orca Servers → Add Server.
The URL uses `127.0.0.1` because both the desktop client and the published port are on this Mac.
Choose another port for another sandbox. Do not expose it publicly, commit the log, or share its pairing token.
Keep desktop and server versions compatible. Installed servers are not automatically upgraded by this adapter.
Select the paired runtime as the default host for its projects; avoid accidentally creating Local workspaces.

This combines documented Docker port publishing with Orca's beta headless server. It is not Docker's documented
Orca SSH integration and still requires an Apple Silicon end-to-end test, including provider auth and chat continuation.
The adapter prints “starting”, not a readiness claim: inspect the log before pairing. Linux package dependencies,
remote account features, or protocol mismatches can still prevent startup or a particular feature.
Keep the ordinary SSH/TUI route available if the beta server fails.

The sandbox is put in detached mode to keep the server alive without an attached TUI. Stopping it stops the server.
After restarting, run the `orca` command above again. Closing the desktop UI can preserve remote sessions;
a local VM still cannot run while the Mac sleeps. Long unattended sessions require an awake host.

## Skills and task workflow

`skills.sh` uses `sbx skills add` directly, with no host agent installation or `npx` step.
Use `sbx skills update` to refresh. The shared store is Docker-managed and mounted read-only for supported agents.
Agents outside Docker's shared-skills integration need their own in-sandbox skill setup.

Keep one task branch/worktree per task and a draft PR. Agents can hand off sequentially within it.
Use independent dependency installations, build outputs, databases, and service ports per worktree.
Keep multi-session progress in `HANDOFF.md`. Review before merging.
Project setup commands belong in that project's tooling; `orca.yaml` is optional and should not be mandatory for other clients.

Use Navi for inspect, ports, scoped network rules, native credential prompts, stop, and confirmed deletion.
Updates of agent binaries use the agent's own documented updater inside its sandbox, followed by a session restart.
Refresh changes the shared instruction baseline, so do it between active tasks.
Stopping preserves files; removing a sandbox deletes its ordinary filesystem. Push commits and preserve ignored data first.

## Verification before retiring the old setup

1. Create one fresh sandbox; confirm it has no Mac project workspace mounted using `sbx inspect`.
2. Test GitHub fetch/push, provider auth, the shared skills, and a relevant project build.
3. Create two task worktrees, run tests with separate ports, and confirm secret scanning works from both.
4. Connect Orca and one other client to the same remote task path; use them sequentially.
5. If using full Orca, verify startup, pairing, structured chat, conversation continuation, and reconnect.
6. Stop/restart the sandbox and re-launch its optional server. Check persisted files before any deletion.

Shell/unit/CI checks do not establish that these Mac/VM/client integration checks passed.

Sources: [Docker integrations](https://docs.docker.com/ai/sandboxes/integrations/),
[Orca SSH](https://docs.docker.com/ai/sandboxes/integrations/orca/),
[Docker usage](https://docs.docker.com/ai/sandboxes/usage/),
[shared skills](https://docs.docker.com/ai/sandboxes/workflows/agent-skills/),
[Orca chat](https://github.com/stablyai/orca/blob/main/docs/site/content/docs/agents/native-chat.mdx),
[Orca servers](https://github.com/stablyai/orca/blob/main/docs/site/content/docs/remote-servers.mdx).
