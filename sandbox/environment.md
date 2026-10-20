
## Docker Sandbox environment overrides

- This workspace is explicitly provisioned for autonomous development inside a Docker Sandbox.
- Use Linux commands. The project is /home/agent/workspace, stored inside the sandbox.
- Installing development tools and dependencies inside this sandbox is authorized. Prefer uv and the repository's JS package manager; Linux Homebrew is unnecessary.
- Run project services using the sandbox's Docker daemon when needed. Never request the Mac Docker socket or mount Mac directories.
- Work in task branches/worktrees. Separate project-agent sandboxes have separate clones; exchange committed changes through GitHub.
- Disposable project build/cache files may be removed. Preserve valuable data and other workers' changes.
- The sandbox permits routine execution. Still ask before production changes, spending, expanding credentials, destructive remote actions, or merging.
- Never change host policies, credential forwarding, mounts, or shared skills. Do not search for unrelated credentials.
- For browser testing, install the optional browser with `DOTFILES_SANDBOX=1 bash "$HOME/.local/share/dotfiles-setup/sandbox/bootstrap.sh" --browser`, then use agent-browser.
- Keep project setup, tests, and CI reproducible. A local hook is not a substitute for CI secret scanning.
