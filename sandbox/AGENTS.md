# Docker Sandbox environment

- This session runs inside an isolated Linux Docker Sandbox.
- Installing guest development tools and disposable local services is allowed.
- Never change host mounts, credential bindings, shared skills, or sandbox security.
- Keep work in the assigned project checkout; other worktrees share this VM.
- Use distinct dependencies, build outputs, databases, and service ports per task.
- Use Docker-managed authentication. Never print or copy real tokens.
- Report blocked network destinations instead of bypassing policy.
- Assigned work authorizes coherent commits, task-branch pushes, and one draft PR.
- Do not merge PRs, push to the default branch, or rewrite published history.
- Hand off sequentially in the same worktree; use one active writer per branch.
- Keep multi-session state in tracked HANDOFF.md, excluding secrets.
- Choose reversible implementation decisions and continue through routine work.
- Close browser sessions and disposable services started by the task when finished.
