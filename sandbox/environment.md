
# Docker Sandbox environment

- This is an isolated Linux development environment. Keep project work inside the sandbox.
- Installing development tools and running project-local services is authorized. Preserve valuable data.
- Do not change host mounts, credential bindings, shared skills, or sandbox security settings.
- If network access is blocked, report the hostname, port, command, and purpose. Continue other work without bypassing policy.
- Bind development servers to `0.0.0.0` so ports can be published.
- When using `agent-browser`, reuse named sessions and close them when finished. Avoid accumulating open sessions.
- API keys are proxy-injected placeholders (`sbx-cs-...`). They work as-is. Never ask for real values or write secrets to `.env`.

## Task workflow

- Stay on the assigned branch. Don't create branches or worktrees; the sandbox is your isolation.
- On start: `git status`, `git fetch origin`, read `HANDOFF.md` if present. Fast-forward only when clean; report divergence, never reset or stash.
- Task branches may pass between sandboxes and agents. One active writer per branch.
- Check open PRs and Issues before changing interfaces other tasks depend on.
- Assigned work authorizes commits, task-branch pushes, and one draft PR per task. Keep its description and verification current.
- Large or multi-session tasks: keep plan and state in tracked `HANDOFF.md` (goal, acceptance criteria, progress, decisions, verification, blockers, setup, next action). Update it at milestones and before stopping. Exclude secrets.
- No one may be watching. If a question would block you, choose the most reversible option, record it under "Decisions for review" in the PR, and continue. Stop only for destructive, paid, or credential-expanding actions.
- Before marking ready: `git merge origin/<default>` (never rebase a pushed branch), resolve conflicts, rerun relevant checks, move the handoff summary into the PR description, and delete task-created `HANDOFF.md` in a normal commit. Never delete a `HANDOFF.md` the base branch already has. Leave blocked work in draft.
