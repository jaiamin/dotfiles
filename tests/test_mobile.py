"""Exercise the Mac helper with fake launchd/Tailscale/SSH, real jq and plist parsing."""
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'dot_local/bin/executable_sbx-mobile'

FAKE = r'''
import json, os, pathlib, plistlib, subprocess, sys, time
root = pathlib.Path(os.environ['FAKE_ROOT'])
dbpath = root/'db.json'
db = json.loads(dbpath.read_text())
tool = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
with (root/'calls.jsonl').open('a') as f:
    f.write(json.dumps([tool, *args])+'\n')
def save(): dbpath.write_text(json.dumps(db))
if tool == 'uname': print('Darwin')
elif tool == 'lsof':
    port = next((a.split(':')[-1] for a in args if a.startswith('-iTCP:')), '')
    sys.exit(0 if port in db.get('occupied', []) else 1)
elif tool == 'plutil':
    content = json.load(sys.stdin)
    pathlib.Path(args[args.index('-o')+1]).write_bytes(plistlib.dumps(content))
elif tool == 'launchctl':
    verb = args[0]
    if verb == 'print': sys.exit(0 if args[1].split('/')[-1] in db['jobs'] else 1)
    if verb == 'bootstrap':
        if db.get('bootstrap_fail'): sys.exit(13)
        plist = plistlib.loads(pathlib.Path(args[2]).read_bytes())
        db['jobs'][plist['Label']] = plist
    elif verb == 'bootout': db['jobs'].pop(args[1].split('/')[-1], None)
    save()
elif tool == 'tailscale':
    if args == ['status', '--json']:
        print(json.dumps({'BackendState': db.get('backend', 'Running'),
                          'Self': {'DNSName': 'test-mac.tail-test.ts.net.'}}))
    elif args == ['serve', 'status', '--json']: print(json.dumps(db['serve']))
    else:
        if db.get('serve_fail'): sys.exit(14)
        port = next(a.split('=',1)[1] for a in args if a.startswith('--https='))
        key = 'test-mac.tail-test.ts.net:'+port
        if args[-1] == 'off':
            db['serve']['TCP'].pop(port, None)
            db['serve']['Web'].pop(key, None)
        else:
            db['serve']['TCP'][port] = {'HTTPS': True}
            db['serve']['Web'][key] = {'Handlers': {'/': {'Proxy': args[-1]}}}
        save()
elif tool == 'curl':
    if db.get('https_fail') and args[-1].startswith('https://'): sys.exit(60)
    if os.environ.get('EXEC_REMOTE'):
        if db.get('remote_healthy'): print('{"environmentId":"fixture-env","label":"fixture"}')
        else: sys.exit(7)
    elif db.get('unreachable'): sys.exit(7)
    elif db.get('invalid_response'): print('<html>another service</html>')
    else: print('{"environmentId":"fixture-env","label":"fixture"}')
elif tool == 'ssh':
    if 'bash -s --' in args[-1]:
        remote = sys.stdin.read()
        (root/'remote.sh').write_text(remote)
        if os.environ.get('EXEC_REMOTE'):
            env = dict(os.environ, HOME=str(root/'guest'))
            result = subprocess.run(['bash', '-s', '--', '3773'], input=remote, text=True, env=env)
            sys.exit(result.returncode)
        sys.exit(db.get('ssh_exit', 0))
    if db.get('pair_fail'): sys.exit(16)
    print('Pairing URL: http://127.0.0.1:3773/pair#token=FIXTURE-CODE')
    print('Token: FIXTURE-CODE')
elif tool == 'sleep':
    if os.environ.get('EXEC_REMOTE'):
        if not db.get('remote_healthy'):
            deadline = time.monotonic()+3
            while not (root/'guest-started').exists() and time.monotonic() < deadline:
                time.sleep(.01)
        sys.exit(42)  # End the watchdog after one pass; no live services escape the test.
elif tool == 't3':
    (root/'guest-started').write_text(json.dumps(args))
else: raise RuntimeError(tool)
'''


class MobileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root/'home with spaces'
        self.bin = self.home/'.local/bin'
        self.bin.mkdir(parents=True)
        self.env = dict(os.environ, HOME=str(self.home), FAKE_ROOT=str(self.root),
                        PATH=f'{self.bin}:{os.environ["PATH"]}')
        self.db = {'jobs': {}, 'serve': {'TCP': {}, 'Web': {}}}
        self.save()
        for name in ('uname', 'lsof', 'plutil', 'launchctl', 'tailscale', 'curl', 'ssh', 'sleep', 't3'):
            path = self.bin/name
            path.write_text(f'#!{sys.executable}\n'+FAKE)
            path.chmod(0o755)

    def save(self): (self.root/'db.json').write_text(json.dumps(self.db))
    def read(self): return json.loads((self.root/'db.json').read_text())
    def config(self, name='project'):
        return self.home/f'.local/state/sbx-mobile/{name}.json'
    def run_helper(self, *args):
        return subprocess.run([os.environ.get('TEST_BASH', 'bash'), str(HELPER), *args],
                              env=self.env, capture_output=True, text=True, timeout=30)
    def calls(self):
        return [json.loads(x) for x in (self.root/'calls.jsonl').read_text().splitlines()]
    def setup_bridge(self, name='project'):
        result = self.run_helper(name)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def test_one_command_sets_private_endpoint_login_service_and_terminal_only_code(self):
        result = self.setup_bridge()
        self.assertIn('Address: https://test-mac.tail-test.ts.net:8444', result.stdout)
        self.assertIn('Code: FIXTURE-CODE', result.stdout)
        self.assertEqual(json.loads(self.config().read_text()),
                         {'local_port':44774, 'https_port':8444, 'guest_port':3773})
        plist_path = next((self.home/'Library/LaunchAgents').glob('*.plist'))
        plist = plistlib.loads(plist_path.read_bytes())
        self.assertTrue(plist['RunAtLoad'])
        self.assertTrue(plist['KeepAlive'])
        self.assertEqual(plist['ThrottleInterval'], 30)
        self.assertEqual(plist['ProgramArguments'], ['/bin/bash', str(HELPER), '_run', 'project'])
        self.assertEqual(plist['StandardOutPath'], '/dev/null')
        for path in self.home.rglob('*'):
            if path.is_file() and not path.is_relative_to(self.bin):
                self.assertNotIn(b'FIXTURE-CODE', path.read_bytes())
        self.assertEqual(self.config().stat().st_mode & 0o777, 0o600)

    def test_repeat_reuses_service_and_ports_and_second_sandbox_gets_new_ports(self):
        self.setup_bridge()
        before = self.config().read_bytes()
        self.setup_bridge()
        self.assertEqual(self.config().read_bytes(), before)
        self.assertEqual(sum(c[:2] == ['launchctl','bootstrap'] for c in self.calls()), 1)
        self.setup_bridge('another')
        self.assertEqual(json.loads(self.config('another').read_text())['local_port'], 44775)
        self.assertEqual(json.loads(self.config('another').read_text())['https_port'], 8445)

    def test_skips_manual_serve_and_occupied_local_ports(self):
        self.db['serve'] = {'TCP': {'8444': {'HTTPS':True}},
                            'Web': {'other:8444': {'Handlers': {'/': {'Proxy':'http://127.0.0.1:1234'}}}}}
        self.db['occupied'] = ['44775']
        self.save()
        self.setup_bridge()
        self.assertEqual(json.loads(self.config().read_text())['https_port'], 8446)
        self.assertIn('8444', self.read()['serve']['TCP'])

    def test_rollback_failed_startup_leaves_no_mapping_or_login_service(self):
        for failure in ('unreachable', 'invalid_response', 'bootstrap_fail', 'serve_fail'):
            with self.subTest(failure=failure):
                self.db[failure] = True
                self.save()
                result = self.run_helper('project')
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.config().exists())
                self.assertEqual(self.read()['jobs'], {})
                self.assertEqual(self.read()['serve']['TCP'], {})
                self.assertFalse(list((self.home/'Library/LaunchAgents').glob('*.plist')))
                del self.db[failure]

    def test_pairing_failure_keeps_working_bridge_for_retry(self):
        self.db['pair_fail'] = True
        self.save()
        self.assertNotEqual(self.run_helper('project').returncode, 0)
        self.assertTrue(self.config().exists())
        self.assertTrue(self.read()['jobs'])
        self.assertTrue(self.read()['serve']['TCP'])

    def test_https_failure_does_not_print_a_pairing_code_and_can_be_retried(self):
        self.db['https_fail'] = True
        self.save()
        result = self.run_helper('project')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('Code:', result.stdout)
        self.assertTrue(self.config().exists())
        self.db = self.read()
        self.db.pop('https_fail')
        self.save()
        self.setup_bridge()
        self.assertEqual(sum(c[:2] == ['launchctl','bootstrap'] for c in self.calls()), 1)

    def test_worker_propagates_ssh_failure_so_launchd_can_restart_it(self):
        self.setup_bridge()
        self.db = self.read()
        self.db['ssh_exit'] = 255
        self.save()
        self.assertEqual(self.run_helper('_run','project').returncode, 255)
        self.assertTrue(next(iter(self.read()['jobs'].values()))['KeepAlive'])

    def test_busy_setup_lock_blocks_teardown_and_setup(self):
        self.setup_bridge()
        (self.config().parent/'.lock').mkdir()
        before = self.read()
        for args in [('project',), ('off','project')]:
            self.assertNotEqual(self.run_helper(*args).returncode, 0)
            self.assertEqual(self.read(), before)

    def test_off_removes_only_own_resources_and_never_stops_guest(self):
        self.setup_bridge()
        self.setup_bridge('another')
        result = self.run_helper('off','project')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.config().exists())
        self.assertTrue(self.config('another').exists())
        self.assertEqual(set(self.read()['serve']['TCP']), {'8445'})
        self.assertTrue(self.read()['jobs'])
        self.assertFalse(any(c[0] in ('sbx', 'kill', 'pkill') for c in self.calls()))

    def test_refuses_to_overwrite_or_remove_endpoint_reassigned_to_someone_else(self):
        self.setup_bridge()
        db = self.read()
        db['serve']['Web']['test-mac.tail-test.ts.net:8444']['Handlers']['/']['Proxy'] = 'http://127.0.0.1:9999'
        self.db = db
        self.save()
        for args in [('project',), ('off','project')]:
            self.assertNotEqual(self.run_helper(*args).returncode, 0)
            self.assertEqual(self.read(), db)
            self.assertTrue(self.config().exists())

    def test_status_checks_https_and_reports_missing_service(self):
        self.setup_bridge()
        self.assertEqual(self.run_helper('status','project').returncode, 0)
        self.db = self.read()
        self.db['jobs'] = {}
        self.save()
        self.assertNotEqual(self.run_helper('status','project').returncode, 0)

    def test_disconnected_tailscale_and_invalid_names_make_no_service(self):
        self.db['backend'] = 'Stopped'
        self.save()
        self.assertNotEqual(self.run_helper('project').returncode, 0)
        self.assertFalse(self.config().exists())
        for name in ('x', '../project', 'project;echo', '-oops'):
            self.assertNotEqual(self.run_helper(name).returncode, 0)
        self.assertEqual(self.read()['jobs'], {})

    def test_worker_preserves_healthy_server_or_starts_missing_one_then_allows_reconnect(self):
        self.setup_bridge()
        self.env['EXEC_REMOTE'] = '1'
        for healthy in (True, False):
            with self.subTest(healthy=healthy):
                self.db = self.read()
                self.db['remote_healthy'] = healthy
                self.save()
                result = self.run_helper('_run','project')
                self.assertEqual(result.returncode, 42, result.stderr)
                self.assertEqual((self.root/'guest-started').exists(), not healthy)
                call = [c for c in self.calls() if c[0] == 'ssh'][-1]
                self.assertIn('127.0.0.1:44774:127.0.0.1:3773', call)
                self.assertIn('ExitOnForwardFailure=yes', call)
                self.assertIn('ServerAliveCountMax=3', call)
                self.assertNotIn('sbx ', (self.root/'remote.sh').read_text())


if __name__ == '__main__': unittest.main()
