# Global instructions

## Scale the process to the task
- Prototype (repo AGENTS.md says "This is a prototype."): optimize for speed. Commit to main, test only core logic, no PRs.
- Small (a few files, clear goal): just do it, with tdd for logic. No spec, no questions.
- Medium (a feature with unknowns): short plan → build → code-review.
- Large (multiple modules or days): stop and tell me it's large, with a 3–5 line plan. I'll run /to-spec → /to-tickets → /implement-spec.
- Match effort to size: don't over-engineer small work or under-plan large work.

## Autonomy
- Decide yourself; record assumptions in the PR description.
- Ask me only about product direction, destructive or irreversible actions, spending money, or credentials.
- If requirements are genuinely ambiguous, ask me to run /grill-with-docs instead of guessing.
- When blocked, try another approach. After two failed approaches, stop and report what you tried.
- Other agents may be working in parallel: stay inside your own branch/worktree.
- Keep work resumable by any agent: commit and push often, keep the ticket's GitHub issue current, and when you finish or stop, post a handoff comment (done / in progress / next / gotchas) on the issue or PR.

## Scope
- Change only what the task needs. Note unrelated issues in the PR instead of fixing them.
- Prefer simple solutions. Small, well-known dependencies are fine (list them in the PR); ask before adding heavy ones.

## Definition of done
- Tests, linter, and type checks pass locally, and CI passes on the PR.
- Never make checks pass by skipping or deleting tests, disabling lint rules, or adding type-ignore comments. If one is truly needed, explain why in the PR.
- UI work: design with impeccable, audit with web-design-guidelines, check in a browser with agent-browser.
- Report anything you couldn't verify. Never claim success you didn't confirm.

## Git
- One branch per task or worktree; commit freely there.
- When done, push the branch and open a PR. Never push to main, merge, or force-push.
- Commits: Conventional Commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`), imperative subject, body only for a non-obvious "why".

## Safety
- Never read, print, or commit secrets or .env files; use .env.example for templates.
- Ask before destructive commands (rm -rf, dropping data, rewriting history), global installs, or piping remote scripts to a shell (`curl | sh`).

## Environment/Tools
- Delete files with `trash`, never `rm`.
- Run `gitleaks protect --staged` before every commit. Stop if it flags anything. Never write secrets to files. Read them from env vars.
- macOS. Python: uv only (`uv run`, `uv add`), never pip. Node via Homebrew.
- If a `justfile` exists, use its recipes for build, test, and lint. If not, create one for reusable commands.
- Use `ast-grep` for structural search or multi-file refactors.
- Project-specific commands live in each repo's AGENTS.md; follow them over these defaults.
- Context7: use the installed `ctx7` command, never `npx ctx7`.

## Communication
- Be concise and honest: result first, then what I need to decide.
- Explain non-obvious choices in one line so I learn from them.
