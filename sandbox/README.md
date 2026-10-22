# Docker Sandboxes

Autonomous projects run in persistent Linux sandboxes without mounting Mac project folders. Herdr stays on the Mac; native agents remain supervised.

Use current `sbx`. Kits, environment files, and shared skills are evolving features.

## Once per Mac

Complete the root README first, then:

```sh
sbx login
sbx settings set ssh.agentForwardingEnabled false
sbx settings set skills.defaultMode readonly
sbx daemon restart
sbx setup ssh
sbx secret set github --command 'env -u GH_TOKEN -u GITHUB_TOKEN gh auth token --hostname github.com'
sbx secret set openai --oauth
sbx skills import
```

On a fresh installation, run `sbx policy init balanced`. Otherwise inspect `sbx policy ls --wide`.

Claude subscription users use `/login` inside Claude. OpenCode needs its own supported provider. Keep production credentials out; the GitHub command delegates your existing token’s permissions.


## Create and continue tasks

Use Navi's "Create a new task sandbox" command for new work.

Provide:
- Repository: `jaiamin/bignums`
- Task: `auth`
- Agent: `claude`, `codex`, or `opencode`
- Browser: `false` or `true`

Each new task gets an isolated checkout and a unique
`agent/<task>-<hash>` branch.

For a handoff, first have the current agent commit and
push its work and HANDOFF.md, then stop that agent.

Use Navi's "Continue an existing task in a new sandbox"
command. Select the repository and existing remote branch,
then choose the next agent.

The new sandbox checks out the same task branch and
reuses its existing work and handoff. Do not run two
writers on that branch simultaneously.

To reopen an existing sandbox without changing its agent,
use Navi's existing "Reopen sandbox" command.

For multi-session work:
- Keep HANDOFF.md on the task branch while work continues.
- Maintain one draft PR per task.
- Transfer the final handoff to the PR description and
  remove task-created HANDOFF.md before the PR is ready.
- Do not merge until checks pass and integration is reviewed.

The task branch must exist on GitHub before another
sandbox can take over. Local-only changes are not shared.

## Daily use

Reopen an existing sandbox:

```sh
HERDR_AGENT=claude sbx run --name bignums-claude
```

Use one Herdr workspace per project. Local refers to the Mac Herdr server. `HERDR_AGENT` helps status detection; it does not change permissions.

Avoid bare `sbx run claude` for creation because it mounts the current Mac directory.

## Preview and inspect

Ask the agent to bind its server to `0.0.0.0`, then run on the Mac:

```sh
sbx ports bignums-claude --publish 5173:5173
open http://localhost:5173
ssh bignums-claude.sbx
```

The project lives at `/home/agent/workspace`. Use another host port for another project, such as `5174:5173`.

## Maintain

```sh
sbx ls
sbx policy approval ls
sbx policy log
sbx diagnose
sbx stop bignums-claude
```

Allow a required destination on the Mac:

```sh
sbx policy allow network --sandbox bignums-claude example.com:443
```

Existing guests do not automatically update. To refresh instructions and configuration, run inside Linux:

```sh
git -C ~/.dotfiles pull --ff-only
bash ~/.dotfiles/sandbox/bootstrap.sh jaiamin/bignums
```

Restart the agent afterward. Update guest tools and project dependencies separately. After updating Mac skills, rerun `sbx skills import`.

Stopping preserves files but ends processes. Removal deletes internal data:

```sh
# Preserve code, databases, and untracked files first.
sbx rm bignums-claude
```

Push important work regularly. Chezmoi does not back up sandboxes. Avoid blanket prune/reset commands.

Routine coding runs autonomously. Initial login, network approvals, and consequential decisions may still need attention. Agent instructions are not enforced approval gates.
