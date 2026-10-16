# Global instructions

## Scale the process to the task
- Small (a few files, clear goal): just do it, with tdd for logic. No spec, no questions.
- Medium (a feature with unknowns): short plan → implement → code-review.
- Large (multiple modules or days): to-spec → to-tickets → implement-spec or an agent team, one worktree per ticket.
- Match effort to size: don't over-engineer small work or under-plan large work.

## Autonomy
- Decide yourself; record assumptions in the PR description.
- Ask me only about product direction, destructive or irreversible actions, spending money, or credentials.
- Use grill-me only when requirements are genuinely ambiguous.
- When blocked, try another approach first. If you stop partway, leave a handoff note.

## Scope
- Change only what the task needs. Note unrelated issues in the PR instead of fixing them.
- Prefer simple solutions. Small, well-known dependencies are fine (list them in the PR); ask before adding heavy ones.

## Definition of done
- Tests, linter, and type checks pass locally, and CI passes on the PR.
- UI changes checked in a browser (agent-browser).
- Report anything you couldn't verify. Never claim success you didn't confirm.

## Git
- One branch per task or worktree; commit freely there.
- When done, push the branch and open a PR. Never push to main, merge, or force-push.
- Exception: repos whose AGENTS.md says "This is a prototype." may commit to main.
- Commits: Conventional Commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`), imperative subject, body only for a non-obvious "why".

## Safety
- Never read, print, or commit secrets or .env files; use .env.example for templates.
- Ask before destructive commands (rm -rf, dropping data, rewriting history).

## Environment
- macOS. Python: uv only (`uv run`, `uv add`), never pip. Node via Homebrew.
- Project-specific commands live in each repo's AGENTS.md; follow them over these defaults.

## Communication
- Be concise and honest: result first, then what I need to decide.
- Explain non-obvious choices in one line so I learn from them.
