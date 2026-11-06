# OpenAI OAuth and project API routing probe

This is an opt-in experiment for sbx 0.51.0+. It does not replace the default
T3 setup or modify existing project sandboxes. It must pass live on the Mac
before its credential declarations are adopted for normal project creation.

The `codex-oauth` v3 workload reuses a pinned, multi-platform Docker Codex image.
Its `openai` service declares OAuth only, with `chatgpt.com` as its resource host.
The `project-openai` v3 mixin declares a different service for `api.openai.com`,
injecting its API key through the standard `OPENAI_API_KEY` variable. It has no
OAuth declaration. The two services never claim the same resource host.

The existing global `openai` OAuth login remains the source of Codex authentication.
The helper stores the API key as `project-openai` scoped to the dedicated probe.
It never stores an API key as `openai`, changes global secrets, edits bindings
files directly, or puts a real key in a command argument, environment file, or
sandbox file. Docker records approved kit bindings in its normal host store.
Docker can request approval for these kit credentials; approve OpenAI OAuth only
for `auth.openai.com`/`chatgpt.com`, and `project-openai` only for `api.openai.com`.

From the repository checkout on the Mac:

```sh
bash sandbox/oauth-api-probe.sh create
```

The helper creates `codex-api-probe-r2` without a host workspace mount and includes
both kits in the initial `sbx create` command. Approve both credential bindings
even if `project-openai` is not set yet. Docker may warn that no API key is stored;
that is expected at this stage. The helper then prompts for the sandbox-scoped
API key through `sbx secret set`, and runs both live checks. It never uses
`sbx kit add`: sbx 0.51 cannot wire new credentials through that recreate flow.
An explicit creation-time environment value supplies only the public
`proxy-managed` sentinel, so standard SDK environment lookup works immediately.
Source builds use Docker's builder sandbox when host Docker is unavailable.
Building the kit can take several minutes on the first run. The probe has no
T3 kit or project checkout; this first experiment isolates authentication.
It is not intended as a project development environment.

The check makes one small paid Responses API request (`gpt-4.1-mini`, at most 32
output tokens) and one Codex subscription turn. Success must print both:

```text
PASS project API: HTTP 200, gpt-4.1-mini, API_OK
PASS Codex OAuth: ChatGPT endpoint, OAUTH_OK
```

Each run uses the normal inspected sandbox network path. It does not bypass the
proxy, disable TLS verification, or copy real OAuth tokens. The API response must
match the expected output; a bare HTTP 200 is insufficient. Codex configuration
is checked before either call to reject an accidental platform-API route.

The helper refuses occupied names and names outside `codex-api-probe[-SUFFIX]`.
The original `codex-api-probe` created by the kit-add experiment is left untouched.
It cannot be repaired by `configure`; create a new probe using the updated helper.
To retry key configuration after a successful creation, or rotate only this
probe's API key:

```sh
bash sandbox/oauth-api-probe.sh configure
```

To repeat the two requests after a successful setup:

```sh
bash sandbox/oauth-api-probe.sh verify
```

Failures preserve the probe for inspection; no automatic deletion or rollback
touches another sandbox. Capture the helper's PASS/FAIL output. Do not share keys,
auth files, full process environments, or raw provider logs.

This removes a documented routing ambiguity, but schema checks and mocked tests
cannot establish whether the current closed-source sbx proxy honors it. Both
real checks are required. No change to `manage.sh`, Navi, or the default kit list
should be made until that result is observed.

Sources: [Docker credential declarations](https://docs.docker.com/ai/sandboxes/configuration/credentials/),
[host routing limitation](https://github.com/docker/sbx-releases/issues/615#issuecomment-5928643434),
[custom-secret regression](https://github.com/docker/sbx-releases/issues/601),
[OAuth override report](https://github.com/docker/sbx-releases/issues/793).
Docker's [custom-service walkthrough](https://docs.docker.com/learn/content/working-with-sandbox-secrets/)
documents declaring a credential at creation, approving its binding while unset,
and then supplying its value to the existing sandbox.
