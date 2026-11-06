"""Probe boundaries and response validation; no live credentials or model calls."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

try:
    import yaml
except ImportError:
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "sandbox/oauth-api-probe.sh"
HOST_BASH = os.environ.get("TEST_BASH", "bash")
spec = importlib.util.spec_from_file_location("oauth_api_verify", ROOT / "sandbox/oauth_api_verify.py")
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)


@unittest.skipUnless(yaml, 'kit descriptor checks need PyYAML (installed in Linux CI)')
class KitRoutingTests(unittest.TestCase):
    def load(self, name):
        return yaml.safe_load((ROOT / 'sandbox/kits' / name / 'spec.yaml').read_text())

    def test_oauth_and_project_credentials_never_share_a_resource_host(self):
        credentials = []
        for name in ('codex-oauth', 'project-openai'):
            descriptor = self.load(name)
            self.assertEqual(descriptor['schemaVersion'], '3')
            credentials.extend(c['config'] for c in descriptor['capabilities']
                               if c['type'] == 'com.docker.sandbox/credential@1')
        by_service = {c['service']: c for c in credentials}
        self.assertEqual(set(by_service), {'openai', 'project-openai'})
        self.assertNotIn('apiKey', by_service['openai'])
        self.assertEqual(by_service['openai']['oauth']['resourceHosts'], ['chatgpt.com'])
        project = by_service['project-openai']
        self.assertNotIn('oauth', project)
        self.assertEqual(project['apiKey']['name'], 'OPENAI_API_KEY')
        self.assertTrue(project['apiKey']['proxyManaged'])
        self.assertEqual(project['apiKey']['inject'], [
            {'domain': 'api.openai.com', 'header': 'Authorization', 'format': 'Bearer %s'}])

    def test_real_seed_script_generates_expected_config_and_rejects_api_mode(self):
        descriptor = self.load('codex-oauth')
        lifecycle = next(c['config'] for c in descriptor['capabilities']
                         if c['type'] == 'com.docker.sandbox/lifecycle@1')
        source = lifecycle['install'][0]['command']
        for mode in ('oauth', 'apikey', 'none'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                home = Path(directory)
                result = subprocess.run(['sh', '-c', source.replace('/home/agent', str(home))],
                                        env=dict(os.environ, SBX_CRED_OPENAI_MODE=mode),
                                        capture_output=True, text=True)
                if mode == 'oauth':
                    self.assertEqual(result.returncode, 0, result.stderr)
                    verify.verify_oauth_config(home)
                    self.assertEqual(json.loads((home / '.codex/auth.json').read_text()),
                                     {'OPENAI_API_KEY': 'proxy-managed'})
                else:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse((home / '.codex/config.toml').exists())


class HostProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.log = self.root / "calls.jsonl"
        self.state = self.root / "state.json"
        self.env = dict(os.environ, PATH=f"{self.bin}:{os.environ['PATH']}",
                        PROBE_LOG=str(self.log), PROBE_STATE=str(self.state))
        stub = self.bin / "sbx"
        stub.write_text('''#!/usr/bin/env python3
import json, os, pathlib, sys
a = sys.argv[1:]
with open(os.environ['PROBE_LOG'], 'a') as f: f.write(json.dumps(a) + '\\n')
p = pathlib.Path(os.environ['PROBE_STATE'])
s = json.loads(p.read_text()) if p.exists() else {}
def save(): p.write_text(json.dumps(s))
if a == ['--version']: print(os.environ.get('SBX_VERSION', 'sbx version v0.51.0 test')); sys.exit(0)
if a == ['ls', '-q']: print(os.environ.get('EXISTING', '')); sys.exit(0)
if a[0] == 'create':
    if os.environ.get('FAIL_CREATE'): sys.exit(13)
    s['exists'] = True; save(); sys.exit(0)
if a[:2] == ['secret', 'set']:
    sys.exit(17 if os.environ.get('FAIL_SECRET') else 0)
if a[:2] == ['kit', 'add']:
    raise SystemExit('credential-bearing kit add is unsupported')
if a[0] == 'cp': sys.exit(0)
if a[0] == 'exec':
    c = a[a.index('--') + 1:]
    if c[0] == 'test': sys.exit(0 if s.get(c[-1]) else 1)
    if c[0] == 'touch': s[c[-1]] = True; save(); sys.exit(0)
    if c[0] == 'mkdir': sys.exit(0)
    if c[0] == 'sh': sys.exit(0)
    if c[0] == 'python3':
        if os.environ.get('FAIL_VERIFY'): sys.exit(23)
        print('mock verifier completed'); sys.exit(0)
raise SystemExit('Unexpected probe command')
''')
        stub.chmod(0o755)

    def run_probe(self, *args):
        return subprocess.run([HOST_BASH, str(SCRIPT), *args], env=self.env,
                              capture_output=True, text=True)

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def test_create_scopes_api_key_and_never_changes_global_oauth(self):
        result = self.run_probe("create")
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.calls()
        self.assertIn(['secret', 'set', 'project-openai', '--sandbox', 'codex-api-probe-r2'], calls)
        create = next(c for c in calls if c[0] == 'create')
        self.assertEqual(create[2:], [
            '--kit', str(ROOT / 'sandbox/kits/project-openai'),
            '--name', 'codex-api-probe-r2', '--cpus', '2', '--memory', '4g',
            '--skills', 'off', '--env', 'OPENAI_API_KEY=proxy-managed'])
        self.assertFalse(any(c[0] in ('rm', 'settings', 'policy') for c in calls))
        self.assertFalse(any(c[:3] == ['secret', 'set', 'openai'] for c in calls))
        self.assertFalse(any(c[0] == 'kit' for c in calls))
        self.assertLess(calls.index(create), calls.index(
            ['secret', 'set', 'project-openai', '--sandbox', 'codex-api-probe-r2']))

    def test_refuses_project_names_and_old_versions(self):
        self.assertNotEqual(self.run_probe('create', 'ass').returncode, 0)
        self.assertEqual(self.calls(), [])
        self.env['SBX_VERSION'] = 'sbx version v0.50.0 test'
        self.assertNotEqual(self.run_probe('create').returncode, 0)
        self.assertEqual(self.calls(), [['--version']])

    def test_refuses_existing_or_unmarked_sandboxes(self):
        self.env['EXISTING'] = 'ass\ncodex-api-probe-r2'
        self.assertNotEqual(self.run_probe('create').returncode, 0)
        self.assertFalse(any(c[0] == 'create' for c in self.calls()))
        self.assertNotEqual(self.run_probe('configure').returncode, 0)
        self.assertFalse(any(c[0] == 'secret' for c in self.calls()))

    def test_create_failure_never_sets_a_key(self):
        self.env['FAIL_CREATE'] = '1'
        self.assertNotEqual(self.run_probe('create').returncode, 0)
        self.assertFalse(any(c[0] in ('secret', 'kit', 'cp') for c in self.calls()))

    def test_secret_failure_preserves_probe_without_false_success(self):
        self.env['FAIL_SECRET'] = '1'
        result = self.run_probe('create')
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(json.loads(self.state.read_text())['exists'])
        self.assertFalse(any(c[0] in ('rm', 'cp', 'kit') for c in self.calls()))
        self.assertIn('configure', result.stderr)

    def test_configure_can_resume_after_secret_failure_without_adding_kits(self):
        self.env['FAIL_SECRET'] = '1'
        self.assertNotEqual(self.run_probe('create').returncode, 0)
        self.env.pop('FAIL_SECRET')
        self.assertEqual(self.run_probe('configure').returncode, 0)
        self.log.unlink()
        self.assertEqual(self.run_probe('configure').returncode, 0)
        self.assertFalse(any(c[:2] == ['kit', 'add'] for c in self.calls()))

    def test_old_kit_add_probe_cannot_be_configured_or_verified(self):
        self.state.write_text(json.dumps({
            'exists': True,
            '/home/agent/.config/dotfiles/oauth-api-probe/created': True,
        }))
        for action in ('configure', 'verify'):
            with self.subTest(action=action):
                result = self.run_probe(action, 'codex-api-probe')
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('creation-time API wiring', result.stderr)
        self.assertFalse(any(c[0] in ('create', 'secret', 'kit', 'rm', 'cp') for c in self.calls()))

    def test_verify_is_read_only_for_secrets_and_propagates_failure(self):
        self.assertEqual(self.run_probe('create').returncode, 0)
        self.log.unlink()
        self.env['FAIL_VERIFY'] = '1'
        result = self.run_probe('verify')
        self.assertEqual(result.returncode, 23)
        self.assertFalse(any(c[0] in ('create', 'secret', 'kit', 'rm') for c in self.calls()))
        self.assertNotIn('Both checks passed', result.stdout)


class GuestProbeTests(unittest.TestCase):
    def test_configuration_guard_rejects_platform_api_before_any_request(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / '.codex').mkdir()
            (home / '.codex/config.toml').write_text('model_provider="openai"\n')
            with patch.object(verify.Path, 'home', return_value=home), \
                 patch.object(verify, 'verify_api') as api, \
                 patch.object(verify, 'verify_codex') as codex, \
                 contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(verify.main(), 1)
                api.assert_not_called()
                codex.assert_not_called()

    def test_api_uses_only_platform_endpoint_and_standard_sentinel(self):
        response = io.BytesIO(json.dumps({'output': [{'content': [
            {'type': 'output_text', 'text': 'API_OK'}]}]}).encode())
        response.status = 200
        with patch.dict(os.environ, OPENAI_API_KEY='proxy-managed'), \
             patch.object(verify.urllib.request, 'urlopen', return_value=response) as call, \
             contextlib.redirect_stdout(io.StringIO()):
            verify.verify_api()
        call.assert_called_once()
        request = call.call_args.args[0]
        self.assertEqual(request.full_url, 'https://api.openai.com/v1/responses')
        self.assertEqual(request.get_header('Authorization'), 'Bearer proxy-managed')
        payload = json.loads(request.data)
        self.assertEqual(payload['model'], 'gpt-4.1-mini')
        self.assertEqual(payload['max_output_tokens'], 32)

    def test_http_401_does_not_echo_provider_body_and_codex_is_still_tested(self):
        error = urllib.error.HTTPError('https://api.openai.com/v1/responses', 401, '', {},
                                      io.BytesIO(b'api.responses.write PRIVATE_PROVIDER_TEXT'))
        stderr = io.StringIO()
        with patch.object(verify, 'verify_oauth_config'), \
             patch.dict(os.environ, OPENAI_API_KEY='proxy-managed'), \
             patch.object(verify.urllib.request, 'urlopen', side_effect=error) as call, \
             patch.object(verify, 'verify_codex') as codex, \
             contextlib.redirect_stderr(stderr):
            self.assertEqual(verify.main(), 1)
        call.assert_called_once()
        codex.assert_called_once()
        self.assertIn('HTTP 401 (missing api.responses.write)', stderr.getvalue())
        self.assertNotIn('PRIVATE_PROVIDER_TEXT', stderr.getvalue())

    def test_arbitrary_environment_key_is_refused_without_network(self):
        with patch.dict(os.environ, OPENAI_API_KEY='not-the-service-sentinel'), \
             patch.object(verify.urllib.request, 'urlopen') as call:
            with self.assertRaises(RuntimeError):
                verify.verify_api()
            call.assert_not_called()

    def test_codex_must_return_expected_message_not_just_exit_zero(self):
        def fake_codex(args, **kwargs):
            output = Path(args[args.index('--output-last-message') + 1])
            output.write_text('unrelated result')
            return subprocess.CompletedProcess(args, 0, b'', b'PRIVATE_CLI_LOG')
        with patch.object(verify.subprocess, 'run', side_effect=fake_codex):
            with self.assertRaisesRegex(RuntimeError, 'expected OAuth test response'):
                verify.verify_codex()

    def test_codex_success_uses_ephemeral_session_and_both_checks_required(self):
        def fake_codex(args, **kwargs):
            self.assertIn('--ephemeral', args)
            self.assertIn('--skip-git-repo-check', args)
            self.assertEqual(kwargs['stdin'], subprocess.DEVNULL)
            self.assertIn('model_providers.sandboxd.request_max_retries=0', args)
            self.assertIn('model_providers.sandboxd.stream_max_retries=0', args)
            output = Path(args[args.index('--output-last-message') + 1])
            output.write_text('OAUTH_OK\n')
            return subprocess.CompletedProcess(args, 0, b'', b'')
        with patch.object(verify.subprocess, 'run', side_effect=fake_codex), \
             contextlib.redirect_stdout(io.StringIO()) as stdout:
            verify.verify_codex()
        self.assertIn('PASS Codex OAuth', stdout.getvalue())
        with patch.object(verify, 'verify_oauth_config'), \
             patch.object(verify, 'verify_api'), \
             patch.object(verify, 'verify_codex', side_effect=RuntimeError('OAuth failed')), \
             contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(verify.main(), 1)

    def test_codex_gets_eof_even_when_the_verifier_input_pipe_is_held_open(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary = root / 'codex'
            binary.write_text(f'#!{sys.executable}\n' + '''import sys
from pathlib import Path
assert sys.stdin.read() == ''
Path(sys.argv[sys.argv.index('--output-last-message') + 1]).write_text('OAUTH_OK')
''')
            binary.chmod(0o755)
            code = ('import sys; sys.path.insert(0, sys.argv[1]); '
                    'from oauth_api_verify import verify_codex; verify_codex()')
            process = subprocess.Popen(
                [sys.executable, '-c', code, str(ROOT / 'sandbox')],
                env=dict(os.environ, PATH=f'{root}:{os.environ["PATH"]}'),
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            try:
                # wait(), unlike communicate(), leaves the input pipe open.
                self.assertEqual(process.wait(timeout=10), 0)
                self.assertIn(b'PASS Codex OAuth', process.stdout.read())
            finally:
                process.stdin.close()
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=5)
                process.stdout.close()
                process.stderr.close()

    def test_timeout_reports_stdin_hint_but_redacts_credentials(self):
        error = subprocess.TimeoutExpired('codex', 120, stderr=(
            b'Reading additional input from stdin...\n'
            b'Authorization: Bearer private-value\n'
            b'api_key="private-assignment"\n'
            b'sk-proj-private-key-value'))
        with patch.object(verify.subprocess, 'run', side_effect=error), \
             contextlib.redirect_stderr(io.StringIO()) as stderr:
            with self.assertRaisesRegex(RuntimeError, 'timed out'):
                verify.verify_codex()
        output = stderr.getvalue()
        self.assertIn('Reading additional input from stdin', output)
        for secret in ('private-value', 'private-assignment', 'sk-proj-private-key-value'):
            self.assertNotIn(secret, output)


if __name__ == '__main__':
    unittest.main()
