# Docker Sandboxes

One task per sandbox, one branch per task, one active writer per branch. Project files stay inside Linux; Herdr runs on the Mac.

## New Mac

Complete the [Mac setup](../README.md), then:

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

On a fresh setup, run `sbx policy init balanced`. Otherwise inspect `sbx policy ls --wide`.

Claude subscription users sign in with `/login` inside Claude. OpenCode needs a supported provider. Use development credentials only.

## Tasks

Run `navi`:

- **Create a new task sandbox:** select a repo, task name, agent, and browser option. The repo must have an initial commit.
- **Continue a pushed task branch with another agent:** select an existing task branch.
- **Reopen sandbox:** return to an existing sandbox.

New tasks use `agent/<task>-<random-id>`. New sandboxes install the latest selected agent.

Before switching agents, commit and push work with `HANDOFF.md`, then stop the old sandbox. Git does not transfer ignored files, databases, or installed dependencies.

Agents maintain one draft PR per task. Review before merging.

## Access

Navi includes SSH, VS Code, ports, network access, stop, and delete commands. Run `sbx ls` to see sandbox names.

Project path: `/home/agent/workspace`. Bind development servers to `0.0.0.0` when publishing ports.

## Update a sandbox

Exit the agent. Inside the sandbox, replace the agent and repo below:

```sh
git -C ~/.dotfiles pull --ff-only &&
DOTFILES_AGENT=claude bash ~/.dotfiles/sandbox/bootstrap.sh jaiamin/bignums
```

Restart the agent afterward. This updates the selected agent, instructions, and configuration. Reopening alone does not update them.

Update project dependencies separately. After updating Mac skills, run `sbx skills import`.

Stopping preserves files. Deleting removes sandbox data, so push work and preserve local data first.
