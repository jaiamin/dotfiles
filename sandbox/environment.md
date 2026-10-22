## Docker Sandbox environment

- This environment is explicitly an isolated Docker Sandbox.
- Use Linux commands. Installing development tools inside this sandbox is authorized.
- Keep project files and services inside the sandbox.
- Never change host mounts, host policies, credential forwarding, or shared skills.
- Ask before introducing paid services, infrastructure outside the isolated workspace, or major architectural changes outside the approved scope.
- Development databases, containers, and services inside an explicitly isolated workspace are authorized. Preserve valuable data.
- If sandbox network policy blocks a required destination, report the hostname, port, failed command, and why access is needed. Ask the user
  to approve it on the host; do not change policy or bypass the block. Continue unblocked work and retry after approval.
- For assigned implementation tasks, commit coherent checkpoints, push the task branch, and create or update its PR without asking.
  Use a draft while work is incomplete; mark ready after relevant checks pass. Include verification results and remaining limitations.
  Reuse the existing branch and PR across agent handoffs. Never merge, enable auto-merge, or push directly to main without explicit approval.
