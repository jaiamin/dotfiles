## Docker Sandbox environment

- This is an isolated Linux Docker Sandbox. Keep project work inside it.
- Installing development tools and running development databases,
  containers, and services inside the sandbox is authorized.
  Preserve valuable data.
- Never change host mounts, host policies, credential forwarding,
  or shared skills.
- If network policy blocks a required destination, report its
  hostname, port, failed command, and purpose. Request host-side
  approval; continue unblocked work and retry after approval.
  Do not change policy or bypass the block.
- Assigned implementation tasks authorize checkpoint commits,
  task-branch pushes, and PR creation or updates without asking.
  Reuse the branch and PR across handoffs. Keep incomplete work
  in draft; mark ready after relevant checks pass. Include
  verification results and remaining limitations.

## Parallel task workflow

- This sandbox owns the Git branch specified in its assigned instructions.
- Never switch to main or another agent's branch.
- Read the assigned GitHub Issue if the task identifies one.
- Inspect relevant open PRs before changing shared interfaces.
- Coordinate dependencies through GitHub Issues and PRs.
- Push checkpoints and maintain one draft PR per task.
- Before marking a PR ready, fetch origin/main and merge it
  into the task branch, resolve conflicts, and rerun checks.
- If integration fails or conflicts cannot be resolved safely,
  leave the PR in draft and report the blocker.
- Never merge PRs without explicit approval.

