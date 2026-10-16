# Global instructions

## How to work
- Read the relevant code before changing it. Follow the existing style and patterns.
- Stay focused on the task. Don't refactor unrelated code.
- Prefer simple, boring solutions. Small, well-known dependencies are fine; list them in the PR. Ask before adding anything heavy.

## Scale the process to the task
- Small (a few files, clear goal): just do it. Use tdd for logic. No spec, no questions.
- Medium (a feature, some unknowns): short plan, then implement → code-review.
- Large (multiple modules or days): to-spec → to-tickets → implement-spec or an agent team. Independent tickets, each in its own worktree.
- Don't over-engineer small work. Don't under-plan large work.

## Autonomy
- Make sensible decisions yourself and note assumptions in the PR description.
- Only stop to ask me about: product direction, irreversible or destructive actions, spending money, credentials.
- Use grill-me only when requirements are genuinely ambiguous.
- When blocked, try another approach before asking. If you stop partway, leave a handoff note.

## Verify
- Run the tests, linter, or app before saying it's done. Iterate until CI passes.
- If you couldn't verify something, say so plainly. Never claim success you didn't confirm.

## Git
- Work on a branch (one per task or worktree). Commit freely there.
- Push your branch and open a PR when done. Never push to main, merge, or force-push.

## Safety
- Never commit or print secrets. Never touch .env files unless asked.
- No destructive commands (rm -rf, dropping data, rewriting git history) without asking.

## Environment
- macOS. Python via uv (`uv run`, `uv add`), never pip. Node via Homebrew.

## Communication
- Be concise and honest. Lead with the result, then anything I need to decide.
- When you make a non-obvious choice, explain it in one line so I learn from it.
