# Project sandboxes

One mountless sandbox per project; one task branch/worktree per writer.
The checkout, agent CLIs, and development tools run in Linux. Connect over SSH from a shell or IDE.
Requires Docker Sandboxes 0.51.0+ and a Debian/Ubuntu agent template.
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

On fresh installs, use `sbx policy init balanced`. Use `sbx secret set openai --oauth`
on the Mac if you use Docker's Codex kit with a ChatGPT subscription.

## Create a sandbox

From the dotfiles source directory, or use Navi:

```sh
bash sandbox/manage.sh create my-project owner/repo claude true
bash sandbox/manage.sh check my-project
# Existing managed sandbox, preserving its checkout and history:
bash sandbox/manage.sh refresh my-project
```

The repo needs an initial commit. The base agent selects the Docker kit and its credential
integration. Every project sandbox gets Codex, Claude Code, Cursor, and Antigravity CLI.
Defaults are 4 CPUs, 4 GiB, and read-only shared skills. Set the browser argument to `true`
for agent-browser and Chromium. Append `-- --memory 8g` for more RAM.
Open a shell with `ssh my-project.sbx` and work in `/home/agent/workspace`.

## Connect T3 Code

In T3: **Settings → Environments → Add environment → SSH**, host `my-project.sbx`.
Docker supplies the SSH user; no identity file is needed. Add a project on that environment
at **/home/agent/workspace**. In **Settings → Providers**, select that environment
and enable the providers you use. T3 downloads and verifies its own versioned SSH server on
first connection. For a standalone `t3` CLI, you can explicitly add `-- --kit docker.io/sbx/t3code:latest`
when creating a sandbox. [T3 SSH setup](https://github.com/pingdotgg/t3code/blob/main/docs/user/remote-access.md#desktop-managed-ssh)

| Provider | Sign in on the project environment |
| --- | --- |
| Codex | Use the Docker Codex kit's OAuth, or `codex login --device-auth` in the sandbox for a standalone ChatGPT login. |
| Claude Code | Run `claude auth login` in the sandbox. |
| Cursor | Run `agent login` in the sandbox. T3 uses the `cursor-agent` executable. |
| Gemini via Antigravity | In T3, set the Antigravity binary path to `/home/agent/.local/bin/agy` and use **Sign in**. Update an older T3 environment if it lacks this option. |

Google moved personal Gemini CLI accounts to Antigravity. See [Google's migration guide](https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/) and [T3's Antigravity setup](https://github.com/pingdotgg/t3code/blob/main/docs/user/providers-antigravity.md).

When you hit a usage limit, finish the running turn and choose **New thread in this worktree**
from T3's branch toolbar. Pick another signed-in provider and pass it the task and any open issues.

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

## Worktrees

Use one writer per worktree and separate service ports for parallel tasks. Use a separate
sandbox when tasks need separate VMs. In T3, **New worktree** creates the checkout.
**Settings → Worktrees → Cleanup** controls eligible T3 worktrees. T3 skips live sessions
and open terminals, and checks local changes according to the selected policy. For shell work,
use Git's `worktree` commands. [T3 cleanup settings](https://github.com/pingdotgg/t3code/blob/main/docs/user/project-settings.md#storage-cleanup)

## Maintenance and checks

Run **Refresh sandbox agents and tools** between sessions. It updates the four CLIs,
refreshes the sandbox instructions, and preserves the checkout and logins. It reads the
project from the sandbox's Git origin. To finish a partial setup or repair the optional browser,
pass `OWNER/REPO` or `true` after the sandbox name. Use **Check sandbox** to verify SSH,
the checkout, and agent versions.

Model availability comes from your provider accounts. If T3 still shows an old list, refresh
provider status for that environment. Use **Settings → Maintenance** to enable provider update
checks and **Settings → Environments** to update T3 itself.

Use **Allow one network host in sandbox** for a blocked domain. **Allow all outbound networks in
sandbox** adds a wildcard for that project. **Remove sandbox-wide network rule** removes that
wildcard after confirmation. Docker's explicit deny rules still apply.

**Publish sandbox port to localhost** takes the Mac port and the sandbox port. Use the same
pair to remove the mapping. **List sandbox ports** shows what is currently published. Push or
back up sandbox-only work before using **Delete sandbox and its files**.

[Docker connection](https://docs.docker.com/ai/sandboxes/integrations/t3-code/) ·
[T3 permissions](https://github.com/pingdotgg/t3code/blob/main/docs/user/permission-modes.md) ·
[T3 updates](https://github.com/pingdotgg/t3code/blob/main/docs/user/updating.md)
