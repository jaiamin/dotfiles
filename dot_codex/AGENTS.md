# Global instructions

## Scale the process to the task
- Prototype (repo AGENTS.md says "This is a prototype."): optimize for speed. Commit and push to main, test only core logic, no PRs.
- Small (a few files, clear goal): just do it, with TDD for logic. No spec, no questions.
- Medium (a feature with unknowns): short plan, build, then run the code-review skill.
- Large (multiple modules or days): stop, tell me it's large, and give a 3-5 line plan. I'll run the to-spec, to-tickets, and implement-spec skills.

## Autonomy
- Decide yourself; record assumptions in the PR description.
- Ask me only about product direction, destructive or irreversible actions, spending money, or credentials.
- If requirements are genuinely ambiguous, ask me to run the grill-with-docs skill instead of guessing.
- When blocked, try another approach. After two failed approaches, stop and report what you tried.
- Other agents may work in parallel: stay inside your own branch/worktree.
- Commit and push often. If the task has a GitHub issue, keep it current and post a handoff comment (done / in progress / next / gotchas) when you finish or stop.

## Scope
- Change only what the task needs. Note unrelated issues in the PR instead of fixing them.
- Prefer simple solutions. Before adding a dependency, confirm the exact package exists and is maintained. List new deps in the PR; ask before heavy ones.
- In repos I don't own: follow CONTRIBUTING.md, existing tooling, and commit style over these defaults. Don't add files or config they don't use.

## Definition of done
- Tests, linter, and type checks pass locally. After opening the PR, run `gh pr checks --watch` and fix failures.
- Never make checks pass by skipping or deleting tests, disabling lint rules, or adding type-ignore comments. If one is truly needed, explain why in the PR.
- UI work: design with the impeccable skill, audit with the web-design-guidelines skill, and verify in a browser with `agent-browser`.
- Report anything you couldn't verify. Never claim success you didn't confirm.

## Git
- One branch per task or worktree; commit freely there.
- When done, push the branch and open a PR. Never push to main (except prototypes), merge, or force-push.
- Never bypass hooks with `--no-verify`. If the gitleaks hook flags something, stop and tell me.
- Commits: Conventional Commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`), imperative subject, body only for a non-obvious "why".

## Safety
- Never read, print, or commit secrets or .env files. Read secrets from env vars; use .env.example for templates.
- Delete files with `trash`, never `rm`.
- Ask before destructive commands (dropping data, rewriting history), global installs, or piping remote scripts to a shell.

## Tools
- macOS + Homebrew. A repo's AGENTS.md overrides these defaults.
- Python: `uv` only (`uv run`, `uv add`, `uvx` for one-off tools). Never pip.
- JS/TS: use the package manager matching the lockfile; default to `pnpm`. Never install packages globally.
- Commands: use `justfile` recipes if present. In my own repos, add recipes for commands you run repeatedly.
- Structural search or multi-file refactors: `ast-grep`.
- Before using a library API you're unsure of or that may have changed, fetch current docs with `ctx7` (installed; never `npx ctx7`).
- Check shell scripts with `shellcheck` and GitHub Actions workflows with `actionlint`.
- Git hooks: use `prek`, never `pre-commit`. If a repo has `.pre-commit-config.yaml`, run `prek install` once; run all hooks with `prek run --all-files`.

## New projects (my repos)
- Python: uv, ruff (lint + format), pytest, ty.
- TypeScript: pnpm, strict mode, vitest, Biome.
- Add a justfile with `test`, `lint`, `fmt`, and `dev` recipes, plus a CI workflow running them.

## Communication
- Be concise and honest: result first, then what I need to decide.
- Explain non-obvious choices in one line so I learn from them.
