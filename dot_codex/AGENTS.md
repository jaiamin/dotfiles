# Global instructions

## How to work
- Read the relevant code before changing it. Follow the existing style and patterns.
- Keep changes small and focused on the task. Don't refactor or "improve" unrelated code.
- If the request is ambiguous or a decision is hard to reverse, ask before acting.
- Prefer simple, boring solutions. No new dependencies without asking.

## Verify
- Run the tests, linter, or app to check your work before saying it's done.
- If you couldn't verify something, say so plainly. Never claim success you didn't confirm.

## Safety
- Never commit secrets or print them. Never touch .env files unless asked.
- No destructive commands (rm -rf, force push, dropping data, rewriting git history) without asking.
- Don't commit or push unless I ask.

## Environment
- macOS. Python via uv (`uv run`, `uv add`), never pip. Node via Homebrew.

## Communication
- Be concise and honest. Lead with the result, then anything I need to decide.
- When you make a non-obvious choice, explain it in one line so I learn from it.
