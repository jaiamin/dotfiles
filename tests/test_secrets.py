"""Exercise host key routing and the actual guest export commands without real keys."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'sandbox/secrets.sh'
HOST_BASH = os.environ.get('TEST_BASH', 'bash')


class SecretTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.log = self.root / 'calls.jsonl'
        self.state = self.root / 'state.json'
        self.persistent = self.root / 'persistent.sh'
        self.persistent.write_text('export KEEP_ME=preserved\n')
        self.env = dict(os.environ, PATH=f'{self.bin}:{os.environ["PATH"]}',
                        SECRET_LOG=str(self.log), SECRET_STATE=str(self.state),
                        SECRET_PERSISTENT=str(self.persistent))
        stub = self.bin / 'sbx'
        stub.write_text(f'#!{sys.executable}\n' + '''import json,os,pathlib,subprocess,sys
a=sys.argv[1:]
with open(os.environ['SECRET_LOG'],'a') as f:f.write(json.dumps(a)+'\\n')
p=pathlib.Path(os.environ['SECRET_STATE'])
s=json.loads(p.read_text()) if p.exists() else {'custom':{}}
def save():p.write_text(json.dumps(s))
if a[0]=='exec':
    c=a[a.index('--')+1:]
    if 'created-with-api-kit' in c[2]:
        if os.environ.get('FAIL_EXEC'):sys.exit(125)
        print(os.environ.get('ROUTING','custom'));sys.exit(0)
    c[2]=c[2].replace('/etc/sandbox-persistent.sh',os.environ['SECRET_PERSISTENT'])
    sys.exit(subprocess.run(c).returncode)
if a[:3]==['policy','allow','network']:sys.exit(9 if os.environ.get('FAIL_POLICY') else 0)
if a[:2]==['secret','set']:
    if os.environ.get('FAIL_SECRET'):sys.exit(8)
    s['service']=True;save();sys.exit(0)
if a[:2]==['secret','set-custom']:
    if os.environ.get('FAIL_SECRET'):sys.exit(8)
    fields=dict(zip(a[2::2],a[3::2]));s['custom'][fields['--env']]=fields;save();sys.exit(0)
if a[:2]==['secret','rm']:
    if os.environ.get('FAIL_SECRET'):sys.exit(8)
    if a[2]=='project-openai':
        if not s.get('service'):sys.exit(1)
        s['service']=False
    else:
        fields=dict(zip(a[2::2],a[3::2]))
        if fields['--env-name'] not in s['custom']:sys.exit(1)
        del s['custom'][fields['--env-name']]
    save();sys.exit(0)
raise SystemExit('Unexpected secret helper call')
''')
        stub.chmod(0o755)

    def run_secret(self, action, key='OPENAI_API_KEY', host='api.openai.com'):
        return subprocess.run([HOST_BASH, str(SCRIPT), action, 'my-project', key, host],
                              env=self.env, capture_output=True, text=True)

    def calls(self):
        return [json.loads(x) for x in self.log.read_text().splitlines()] if self.log.exists() else []

    def test_native_project_key_does_not_replace_openai_oauth(self):
        self.env['ROUTING'] = 'service'
        self.assertEqual(self.run_secret('set').returncode, 0)
        calls = self.calls()
        self.assertIn(['secret', 'set', 'project-openai', '--sandbox', 'my-project'], calls)
        self.assertFalse(any(c[:2] == ['secret', 'set-custom'] or c[0] == 'policy' for c in calls))
        self.assertFalse(any(c[:3] == ['secret', 'set', 'openai'] for c in calls))
        self.assertIn('export OPENAI_API_KEY=proxy-managed', self.persistent.read_text())
        self.assertEqual(self.run_secret('remove').returncode, 0)
        self.assertIn(['secret', 'rm', 'project-openai', '--sandbox', 'my-project'], self.calls())
        self.assertEqual(self.persistent.read_text().strip(), 'export KEEP_ME=preserved')

    def test_native_host_supports_custom_sdk_variable_names(self):
        self.env['ROUTING'] = 'service'
        self.assertEqual(self.run_secret('set', 'MY_AI_KEY', 'API.OPENAI.COM').returncode, 0)
        self.assertIn('export MY_AI_KEY=proxy-managed', self.persistent.read_text())
        self.assertEqual(self.run_secret('remove', 'MY_AI_KEY').returncode, 0)

    def test_generic_custom_key_rotation_and_scoped_removal(self):
        for key, host in [('ANTHROPIC_API_KEY', 'api.anthropic.com'), ('CUSTOM_TOKEN', 'api.example.com')]:
            with self.subTest(key=key):
                self.assertEqual(self.run_secret('set', key, host).returncode, 0)
                first = json.loads(self.state.read_text())['custom'][key]['--placeholder']
                self.assertTrue(first.startswith('sbx-cs-'))
                self.assertEqual(self.run_secret('set', key, host).returncode, 0)
                second = json.loads(self.state.read_text())['custom'][key]['--placeholder']
                self.assertNotEqual(first, second)
                self.assertNotIn(first, self.persistent.read_text())
                self.assertEqual(self.persistent.read_text().count(f'export {key}='), 1)
                self.assertEqual(self.run_secret('remove', key, host).returncode, 0)
                self.assertNotIn(f'export {key}=', self.persistent.read_text())
        self.assertIn('export KEEP_ME=preserved', self.persistent.read_text())

    def test_policy_failure_never_registers_or_rotates_custom_secret(self):
        self.env['FAIL_POLICY'] = '1'
        before = self.persistent.read_text()
        self.assertNotEqual(self.run_secret('set', 'CUSTOM_TOKEN', 'api.example.com').returncode, 0)
        self.assertFalse(self.state.exists())
        self.assertFalse(any(c[0] == 'secret' for c in self.calls()))
        self.assertEqual(self.persistent.read_text(), before)

    def test_connection_failure_cannot_select_custom_fallback(self):
        self.env['FAIL_EXEC'] = '1'
        self.assertNotEqual(self.run_secret('set').returncode, 0)
        self.assertFalse(any(c[0] in ('secret', 'policy') for c in self.calls()))

    def test_invalid_variable_or_hostname_is_rejected_before_mutation(self):
        self.assertNotEqual(self.run_secret('set', 'BAD;COMMAND').returncode, 0)
        self.assertNotEqual(self.run_secret('set', host='https://api.openai.com/v1').returncode, 0)
        self.assertEqual(self.calls(), [])

    def test_secret_failure_preserves_existing_exports(self):
        self.env.update(ROUTING='service', FAIL_SECRET='1')
        before = self.persistent.read_text()
        self.assertNotEqual(self.run_secret('set').returncode, 0)
        self.assertNotEqual(self.run_secret('remove').returncode, 0)
        self.assertEqual(self.persistent.read_text(), before)

    @unittest.skipUnless(shutil.which('navi') and shutil.which('fzf'), 'real Navi interpolation needs its CLI and fzf')
    def test_real_navi_commands_route_through_the_helper(self):
        chezmoi = self.bin / 'chezmoi'
        chezmoi.write_text(f'#!{sys.executable}\nprint({str(ROOT)!r})\n')
        chezmoi.chmod(0o755)
        self.env.update(ROUTING='service', sandbox='my-project', key_name='OPENAI_API_KEY', api_host='api.openai.com')
        for query in ('Set project API key', 'Remove project API key'):
            command = subprocess.run(
                ['navi', '--path', str(ROOT / 'dot_local/share/navi/cheats'),
                 '--query', query, '--best-match', '--print'],
                env=self.env, capture_output=True, text=True, check=True,
            ).stdout
            self.assertNotIn('<sandbox>', command)
            result = subprocess.run([HOST_BASH, '-c', command], env=self.env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
