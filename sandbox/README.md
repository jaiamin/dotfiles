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

## Create a project sandbox

Run one of these in a local Herdr pane:

```sh
HERDR_AGENT=claude sbx env run ~/.sbxenv.yaml \
  --name bignums-claude --env-arg repo=jaiamin/bignums

HERDR_AGENT=codex sbx env run ~/.sbxenv.yaml \
  --name bignums-codex --env-arg agent=codex \
  --env-arg repo=jaiamin/bignums

HERDR_AGENT=opencode sbx env run ~/.sbxenv.yaml \
  --name bignums-opencode --env-arg agent=opencode \
  --env-arg repo=jaiamin/bignums
```

Create only what you need. Replace the name and repository for each project. For a new project, create its GitHub repository first:

```sh
gh repo create jaiamin/my-app --private
```

Setup installs tools and instructions, configures Git, and clones the repository automatically. Mac changes must be pushed to GitHub before a new sandbox can see them.

Add `--env-arg browser=true` at creation for browser testing. Defaults are 4 CPUs and 4 GiB; adjust the shared recipe before creating demanding environments.

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
