"""Exercise Navi's real commands and guest file writes without a live sandbox."""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ProjectKeyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / "source"
        (self.source / "sandbox").mkdir(parents=True)
        self.helper = self.source / "sandbox/openai-key.sh"
        shutil.copyfile(ROOT / "sandbox/openai-key.sh", self.helper)
        self.persistent = self.root / "persistent.sh"
        self.persistent.write_text("export KEEP_ME=preserved\nexport OPENAI_API_KEY=proxy-managed\n")
        self.private = self.root / "agent/.config/dotfiles/openai-api.sh"
        self.auth = self.root / "agent/.codex/config.toml"
        self.auth.parent.mkdir(parents=True)
        self.auth.write_text('model_provider = "sandboxd"\n')
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.env = dict(os.environ, PATH=f"{self.bin}:{os.environ['PATH']}",
                        KEY_TEST_ROOT=str(self.root), KEY_TEST_SECRET="sk-fixture-first")
        self.tool("chezmoi", '#!/bin/sh\nprintf "%s/source\\n" "$KEY_TEST_ROOT"\n')
        self.tool("sbx", f"#!{sys.executable}\n" + '''
import getpass, json, os, pathlib, pwd, subprocess, sys, types
root = pathlib.Path(os.environ["KEY_TEST_ROOT"])
a = sys.argv[1:]
with (root/"calls.jsonl").open("a") as stream:
    stream.write(json.dumps(a) + "\\n")
if a[:3] == ["policy", "allow", "network"]:
    sys.exit(23 if os.environ.get("FAIL_POLICY") else 0)
if a[:2] == ["secret", "set-custom"]:
    if os.environ.get("FAIL_SECRET"):
        sys.exit(19)
    pairs = dict(zip(a[2::2], a[3::2]))
    (root/"custom.json").write_text(json.dumps(pairs))
    sys.exit(0)
if a[:2] == ["secret", "rm"]:
    (root/"custom.json").unlink(missing_ok=True)
    sys.exit(0)
if a[0] == "exec":
    command = a[a.index("--") + 1:]
    command = [part.replace("/etc/sandbox-persistent.sh", str(root/"persistent.sh"))
               .replace("/home/agent", str(root/"agent")) for part in command]
    if command[:2] == ["python3", "-c"]:
        getpass.getpass = lambda prompt: os.environ["KEY_TEST_SECRET"]
        pwd.getpwuid = lambda uid: types.SimpleNamespace(pw_uid=os.getuid(), pw_gid=os.getgid())
        if os.environ.get("FAIL_PERSISTENCE"):
            original_replace = os.replace
            def replace(source, destination):
                if str(destination) == str(root/"persistent.sh"):
                    raise OSError("Simulated persistent-file failure")
                return original_replace(source, destination)
            os.replace = replace
        sys.argv = ["guest", command[-1]]
        exec(compile(command[2], "<guest key helper>", "exec"))
    else:
        sys.exit(subprocess.run(command).returncode)
else:
    raise SystemExit("Unexpected sbx call")
''')

    def tool(self, name, content):
        path = self.bin / name
        path.write_text(content)
        path.chmod(0o755)

    def run_helper(self, action, **environment):
        return subprocess.run([os.environ.get("TEST_BASH", "bash"), str(self.helper), action, "review-sandbox"],
                              env=self.env | environment, text=True, capture_output=True)

    def navi_command(self, title):
        lines = (ROOT / "dot_local/share/navi/cheats/sandbox.cheat").read_text().splitlines()
        start = lines.index("# " + title) + 1
        end = next((i for i in range(start, len(lines)) if not lines[i].strip()), len(lines))
        return "\n".join(lines[start:end])

    def run_navi(self, action, host="api.openai.com", key="OPENAI_API_KEY", shell="bash"):
        command = self.navi_command("Set project API key" if action == "set" else "Remove project API key")
        command = command.replace("<sandbox>", "review-sandbox").replace("<api_host>", host).replace("<key_name>", key)
        return subprocess.run([shell, "-c", command], env=self.env, text=True, capture_output=True)

    def calls(self):
        path = self.root / "calls.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def source_environment(self, shell="bash"):
        probe = 'import json, os; print(json.dumps({k: os.environ.get(k) for k in ["OPENAI_API_KEY", "NO_PROXY", "no_proxy", "KEEP_ME"]}))'
        command = '. "$1"; python3 -c ' + shlex.quote(probe)
        env = self.env | {"OPENAI_API_KEY": "proxy-managed", "NO_PROXY": "localhost,internal.example",
                          "no_proxy": "127.0.0.1", "KEEP_ME": "old"}
        result = subprocess.run([shell, "-c", command, "_", str(self.persistent)], env=env,
                                text=True, capture_output=True, check=True)
        return json.loads(result.stdout)

    def test_set_rotate_remove_and_new_process_environment(self):
        for shell in ("bash", "zsh"):
            if not shutil.which(shell):
                continue
            with self.subTest(shell=shell):
                result = self.run_navi("set", shell=shell)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn("sk-fixture", result.stdout + result.stderr)
                self.assertEqual(self.private.stat().st_mode & 0o777, 0o600)
                self.assertEqual(self.private.stat().st_uid, os.getuid())
                self.assertNotIn("sk-fixture", self.persistent.read_text())
                values = self.source_environment(shell)
                self.assertEqual(values["OPENAI_API_KEY"], "sk-fixture-first")
                self.assertEqual(values["NO_PROXY"], "localhost,internal.example,api.openai.com")
                self.assertEqual(values["no_proxy"], "127.0.0.1,api.openai.com")
                self.assertEqual(values["KEEP_ME"], "preserved")
                self.env["KEY_TEST_SECRET"] = "sk-fixture-rotated"
                self.assertEqual(self.run_navi("set", shell=shell).returncode, 0)
                self.assertNotIn("sk-fixture-first", self.private.read_text())
                self.assertEqual(self.persistent.read_text().count("# BEGIN dotfiles OpenAI app key"), 1)
                self.assertEqual(self.source_environment(shell)["OPENAI_API_KEY"], "sk-fixture-rotated")
                self.assertEqual(self.run_navi("remove", shell=shell).returncode, 0)
                self.assertFalse(self.private.exists())
                self.assertNotIn("OpenAI app key", self.persistent.read_text())
                self.assertEqual(self.source_environment(shell)["NO_PROXY"], "localhost,internal.example")
                self.assertEqual(self.auth.read_text(), 'model_provider = "sandboxd"\n')
                self.env["KEY_TEST_SECRET"] = "sk-fixture-first"
        self.assertFalse(any(call[0] == "secret" for call in self.calls()))

    def test_adopts_manual_setup_and_preserves_independent_exclusions(self):
        source = (ROOT / "sandbox/openai-key.sh").read_text()
        code = source.split("guest_code=$(cat <<'PY'\n", 1)[1].split("\nPY\n", 1)[0]
        rules_start = code.index("rules = [")
        rules_end = code.index("\noriginal =", rules_start)
        scope = {}
        exec(code[rules_start:rules_end], scope)
        self.persistent.write_text('export KEEP_ME=preserved\nexport NO_PROXY="localhost,api.openai.com"\n'
                                   'export OPENAI_API_KEY=sk-fixture-manual\n' + "\n".join(scope["rules"]) + "\n")
        self.assertEqual(self.run_helper("set").returncode, 0)
        self.assertNotIn("sk-fixture-manual", self.persistent.read_text())
        self.assertFalse(any(rule in self.persistent.read_text() for rule in scope["rules"]))
        self.assertEqual(self.run_helper("remove").returncode, 0)
        self.assertIn('export NO_PROXY="localhost,api.openai.com"', self.persistent.read_text())

    def test_policy_failure_never_prompts_or_writes(self):
        before = self.persistent.read_text()
        self.assertNotEqual(self.run_helper("set", FAIL_POLICY="1").returncode, 0)
        self.assertFalse(self.private.exists())
        self.assertEqual(self.persistent.read_text(), before)
        self.assertEqual(len(self.calls()), 1)

    def test_invalid_key_preserves_existing_key(self):
        self.assertEqual(self.run_helper("set").returncode, 0)
        before = self.private.read_text(), self.persistent.read_text()
        for key in ("proxy-managed", "sbx-cs-fixture", "", "sk-fixture with spaces"):
            self.assertNotEqual(self.run_helper("set", KEY_TEST_SECRET=key).returncode, 0)
            self.assertEqual((self.private.read_text(), self.persistent.read_text()), before)

    def test_broken_marker_block_is_preserved(self):
        self.persistent.write_text("# BEGIN dotfiles OpenAI app key\nexport KEEP_ME=preserved\n")
        before = self.persistent.read_text()
        self.assertNotEqual(self.run_helper("set").returncode, 0)
        self.assertFalse(self.private.exists())
        self.assertEqual(self.persistent.read_text(), before)

    def test_persistent_write_failure_restores_the_previous_key(self):
        self.assertEqual(self.run_helper("set").returncode, 0)
        before = self.private.read_text(), self.persistent.read_text()
        result = self.run_helper("set", KEY_TEST_SECRET="sk-fixture-new", FAIL_PERSISTENCE="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("sk-fixture-new", result.stdout + result.stderr)
        self.assertEqual((self.private.read_text(), self.persistent.read_text()), before)

    def test_key_is_shell_quoted_and_proxy_append_is_idempotent(self):
        key = "sk-fixture-$(printf${IFS}SHOULD_NOT_EXECUTE)"
        self.assertEqual(self.run_helper("set", KEY_TEST_SECRET=key).returncode, 0)
        for shell in ("bash", "zsh"):
            if not shutil.which(shell):
                continue
            self.assertEqual(self.source_environment(shell)["OPENAI_API_KEY"], key)
            command = '. "$1"; . "$1"; printf "%s" "$NO_PROXY"'
            result = subprocess.run([shell, "-c", command, "_", str(self.persistent)],
                                    env=self.env | {"NO_PROXY": "localhost"},
                                    capture_output=True, text=True, check=True)
            self.assertEqual(result.stdout, "localhost,api.openai.com")

    def test_removing_legacy_custom_key_uses_docker_without_touching_service_oauth(self):
        self.assertEqual(self.run_navi("remove").returncode, 0)
        secret_calls = [call for call in self.calls() if call[0] == "secret"]
        self.assertEqual(secret_calls, [["secret", "rm", "--sandbox", "review-sandbox", "--host",
                                        "api.openai.com", "--env-name", "OPENAI_API_KEY"]])
        self.assertNotIn("OPENAI_API_KEY", self.persistent.read_text())

    def test_anthropic_and_custom_names_keep_original_docker_flow(self):
        for host, key in (("api.anthropic.com", "ANTHROPIC_API_KEY"),
                          ("api.openai.com", "CUSTOM_OPENAI_KEY"), ("api.example.com", "CUSTOM_API_KEY")):
            with self.subTest(host=host, key=key):
                self.assertEqual(self.run_navi("set", host, key).returncode, 0)
                self.assertFalse(self.private.exists())
                stored = json.loads((self.root / "custom.json").read_text())
                self.assertEqual(stored["--host"], host)
                self.assertEqual(stored["--env"], key)
                self.assertIn("sbx-cs-", self.persistent.read_text())
                self.assertNotIn("NO_PROXY", self.persistent.read_text())
                self.assertEqual(self.run_navi("remove", host, key).returncode, 0)
                self.assertNotIn("export " + key + "=", self.persistent.read_text())

    def test_deleting_helper_restores_original_navi_set_and_remove(self):
        self.helper.unlink()
        self.assertEqual(self.run_navi("set").returncode, 0)
        self.assertFalse(self.private.exists())
        self.assertTrue((self.root / "custom.json").exists())
        self.assertIn("export OPENAI_API_KEY=sbx-cs-", self.persistent.read_text())
        self.assertEqual(self.run_navi("remove").returncode, 0)
        self.assertFalse((self.root / "custom.json").exists())


if __name__ == "__main__":
    unittest.main()
