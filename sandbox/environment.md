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
