
# Docker Sandbox environment

- This is an isolated Linux development environment. Keep project work inside the sandbox.
- Installing development tools and running project-local services is authorized. Preserve valuable data.
- Do not change host mounts, credential bindings, shared skills, or sandbox security settings.
- If network access is blocked, report the hostname, port, command, and purpose. Continue other work without bypassing policy.
- When using `agent-browser`, reuse named sessions and close them when finished. Avoid accumulating open sessions.

## Task workflow

- Work only on the assigned branch. Never switch to main or another task branch.
- Task branches may be reused across sandboxes for sequential handoffs, regardless of agent type.
- Before taking over, read HANDOFF.md, fetch origin, and verify the checkout is current.
- One active writer per branch. Concurrent implementers must use separate branches.
- Use GitHub Issues and PRs to coordinate dependencies and shared interfaces.
- Check relevant open PRs before modifying interfaces other tasks depend on.
- Assigned work authorizes checkpoint commits, task-branch pushes, and PR creation.
- Open or update one draft PR per task. Keep its description and verification results current.
- Before marking ready, integrate the latest remote default branch, resolve conflicts, and rerun relevant checks. Leave blocked work in draft.
