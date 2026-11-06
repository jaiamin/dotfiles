"""Guest-only routing check: no SDK dependency and no credential output."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import tomllib
import urllib.error
import urllib.request


def verify_oauth_config(home):
    config = tomllib.loads((home / ".codex/config.toml").read_text())
    provider = config.get("model_providers", {}).get(config.get("model_provider"), {})
    if (
        provider.get("base_url") != "https://chatgpt.com/backend-api/codex"
        or provider.get("experimental_bearer_token") != "oai-oat01-proxy-managed"
        or provider.get("requires_openai_auth") is not False
    ):
        raise RuntimeError("Codex is not configured for the expected proxy-managed OAuth route.")


def verify_api():
    key = os.environ.get("OPENAI_API_KEY")
    if key != "proxy-managed":
        raise RuntimeError("Expected the project service's proxy-managed OPENAI_API_KEY sentinel.")
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps({
            "model": "gpt-4.1-mini",
            "input": "Reply exactly API_OK.",
            "max_output_tokens": 32,
        }).encode(),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            if response.status != 200:
                raise RuntimeError("Project API returned an unexpected HTTP status.")
            body = json.load(response)
    except urllib.error.HTTPError as error:
        # Never echo an error body: providers can include credential fragments.
        body = error.read(65536)
        scope = " (missing api.responses.write)" if b"api.responses.write" in body else ""
        raise RuntimeError(f"Project API: HTTP {error.code}{scope}. No credentials or error body printed.") from None
    except urllib.error.URLError:
        raise RuntimeError("Project API connection failed. No credentials printed.") from None
    text = "".join(
        content.get("text", "")
        for item in body.get("output", [])
        for content in item.get("content", [])
        if content.get("type") == "output_text"
    )
    if text.strip() != "API_OK":
        raise RuntimeError("Project API returned HTTP 200 but not the expected test response.")
    print("PASS project API: HTTP 200, gpt-4.1-mini, API_OK", flush=True)


def show_codex_diagnostics(log):
    """Show a bounded stderr tail without common credential/token formats."""
    if not log:
        print("Codex produced no diagnostic output.", file=sys.stderr)
        return
    text = log.decode(errors="replace") if isinstance(log, bytes) else log
    text = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text)
    text = re.sub(r"(?i)Bearer\s+[^\s\"'<>]+", "Bearer [REDACTED]", text)
    text = re.sub(r"\b(?:sk-|oai-oat|oai-ort|gh[pousr]_|eyJ)[A-Za-z0-9._-]+", "[REDACTED]", text)
    text = re.sub(r"(?i)((?:access_token|refresh_token|api_key)\s*[\"']?\s*[:=]\s*[\"']?)[^\s\"',}]+",
                  r"\1[REDACTED]", text)
    print("Codex diagnostic (redacted):\n" + "\n".join(text.splitlines()[-30:])[-4000:], file=sys.stderr)


def verify_codex():
    with tempfile.TemporaryDirectory(prefix="oauth-api-probe-") as directory:
        result_file = Path(directory) / "response.txt"
        try:
            result = subprocess.run(
                ["codex", "exec", "--ephemeral", "--skip-git-repo-check",
                 "--color", "never",
                 "-c", "model_providers.sandboxd.request_max_retries=0",
                 "-c", "model_providers.sandboxd.stream_max_retries=0",
                 "-c", "model_providers.sandboxd.stream_idle_timeout_ms=20000",
                 "--output-last-message", str(result_file),
                 "Do not use tools. Reply exactly OAUTH_OK."],
                # Codex appends piped stdin to an explicit prompt and waits for
                # EOF. An inherited sbx exec input stream can remain open.
                cwd=directory, stdin=subprocess.DEVNULL, capture_output=True, timeout=120,
            )
        except subprocess.TimeoutExpired as error:
            show_codex_diagnostics(error.stderr)
            raise RuntimeError("Codex OAuth turn timed out after 120 seconds.") from None
        except FileNotFoundError:
            raise RuntimeError("Codex CLI is missing from the probe image.") from None
        if result.returncode:
            show_codex_diagnostics(result.stderr)
            raise RuntimeError(f"Codex OAuth turn failed (exit {result.returncode}); see redacted diagnostics.")
        if not result_file.exists() or result_file.read_text().strip() != "OAUTH_OK":
            raise RuntimeError("Codex did not return the expected OAuth test response.")
    print("PASS Codex OAuth: ChatGPT endpoint, OAUTH_OK", flush=True)


def main():
    try:
        verify_oauth_config(Path.home())
    except (RuntimeError, OSError, ValueError) as error:
        # File and parser errors can contain file contents. Keep these generic.
        message = str(error) if isinstance(error, RuntimeError) else "Probe configuration could not be read."
        print("FAIL " + message, file=sys.stderr)
        return 1
    failed = False
    for check in (verify_api, verify_codex):
        try:
            check()
        except (RuntimeError, OSError, ValueError) as error:
            message = str(error) if isinstance(error, RuntimeError) else "Probe check could not complete."
            print("FAIL " + message, file=sys.stderr)
            failed = True
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
