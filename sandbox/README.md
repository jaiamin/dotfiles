# Docker Sandboxes

One persistent sandbox per active project-agent combination. Projects and dependencies stay inside the sandbox; Mac project folders are not mounted. Requires current `sbx` with mountless creation support (0.42+).

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

If policy was initialized previously, skip `policy init` and inspect `sbx policy ls --wide`. To intentionally replace the policy, `sbx policy reset` clears existing rules, stops running sandboxes, and lets you choose Balanced again.

Docker uses your Mac GitHub CLI credential above. Use a repository-limited sandbox credential when stronger separation is needed. Keep production credentials out. Claude subscription users sign in with `/login` on first launch; do not set an Anthropic API key unless you want API billing. OpenCode providers have separate authentication requirements; select your intended provider and verify billing before using it.

## Work

Run on the Mac, including in a local Herdr pane:

```sh
dev jaiamin/bignums claude
# In another pane, only when needed:
dev jaiamin/bignums codex
dev jaiamin/bignums opencode
```

The name includes owner, repository, and agent: `jaiamin-bignums-claude`. First use provisions and clones; later uses reopen the same sandbox. Each starts with 4 CPUs and a 4 GiB memory limit. Do not run multiple writers in the same checkout; use task worktrees. Separate sandboxes exchange committed branches through GitHub.

Herdr's **Local** label refers to its Mac server, not the execution boundary. Name the workspace `bignums · Claude · Sandbox`; `dev` sets the wrapper hint so Herdr can recognize the sandboxed agent. Herdr is not installed in each sandbox. SSH is only needed for previews, remote editors, or direct inspection.

`dev` refuses existing sandboxes it did not create. It never deletes/recreates a sandbox, changes network policy, pulls your project, or copies Mac authentication directories. It refreshes shared instructions on reopen. Git identity and a portable Gitleaks hook are installed; existing project hooks are preserved. Keep secret scanning in project CI too.

## Browser and preview

Install browser testing only where needed:

```sh
dev jaiamin/bignums claude --browser
```

This adds agent-browser, Playwright Chromium, and its Linux dependencies. The agent can run the browser setup itself using the command in its environment instructions. Headless testing runs inside the sandbox.

For a server listening on sandbox localhost:5173, run in another Mac pane:

```sh
ssh -N -L 127.0.0.1:5173:127.0.0.1:5173 jaiamin-bignums-claude.sbx
```

Open http://localhost:5173 on the Mac. Change both port numbers for another service.

## Check and maintain

```sh
sbx ls
sbx exec -it jaiamin-bignums-claude bash
```

Inside the sandbox, verify `pwd`, `git status`, `gh api user --jq .login`, and `gitleaks version`. For UI projects, verify `agent-browser open https://example.com`, `agent-browser get title`, then `agent-browser close`. Check Herdr's working/idle state and reopen after a stop.

An unfamiliar destination may need host approval. Inspect `sbx policy approval ls`, then allow the specific destination on the Mac, for example:

```sh
sbx policy allow network --sandbox jaiamin-bignums-claude example.com:443
```

Installed guest tools persist; update them explicitly with their package manager/updater when needed. Template updates apply to newly created sandboxes. Use project lockfiles for dependencies. On a new Mac, rerun setup and clone your pushed projects; chezmoi does not back up VM data or running sessions.

```sh
sbx stop jaiamin-bignums-claude
# Only after preserving all needed work, databases, and untracked files:
sbx rm jaiamin-bignums-claude
```

Removal deletes the sandbox's files and services. Avoid blanket `sbx prune` or `sbx reset` for routine cleanup. Closing a Herdr client leaves its server/panes running; stopping a sandbox or rebooting ends its processes, even though files persist. Reconnect with `dev` and resume the agent session as needed.

Mac native agent permissions stay supervised. Sandbox autonomy does not protect external services from credentials you grant: ask before consequential actions, limit credentials, and enforce appropriate GitHub rules/checks.
