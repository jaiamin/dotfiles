"""Boundary tests use a fake sbx; Git behavior uses real local repositories."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MANAGE = ROOT / 'sandbox/manage.sh'
BOOTSTRAP = ROOT / 'sandbox/bootstrap.sh'
HOST_BASH = os.environ.get('TEST_BASH', 'bash')


class ManagerTests(unittest.TestCase):
    def test_native_preferences_exclude_generated_runtime_snapshots(self):
        claude = json.loads((ROOT/'dot_claude/settings.json').read_text())
        self.assertNotIn('hooks', claude)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.log = self.root / 'calls.jsonl'
        self.env = dict(os.environ, PATH=f'{self.bin}:{os.environ["PATH"]}', MOCK_LOG=str(self.log))
        stub = self.bin / 'sbx'
        stub.write_text('''#!/usr/bin/env python3
import json, os, sys
a=sys.argv[1:]
with open(os.environ['MOCK_LOG'],'a') as f: f.write(json.dumps(a)+'\\n')
if a==['ls','-q']: print(os.environ.get('EXISTING',''))
if a[0]=='create' and os.environ.get('FAIL_CREATE'): sys.exit(1)
if a[0]=='exec' and 'test' in a and os.environ.get('UNMANAGED'): sys.exit(1)
''')
        stub.chmod(0o755)

    def run_manager(self, *args):
        return subprocess.run([HOST_BASH, str(MANAGE), *args], env=self.env, text=True, capture_output=True)

    def calls(self):
        return [json.loads(x) for x in self.log.read_text().splitlines()] if self.log.exists() else []

    def test_create_has_no_workspace_mount_or_agent_launch(self):
        result = self.run_manager('create', 'my-project', 'owner/repo', 'codex', 'false')
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.calls()
        create = next(x for x in calls if x[0] == 'create')
        self.assertEqual(create, ['create','codex','--name','my-project','--cpus','4','--memory','4g','--skills','readonly','--kit','docker.io/sbx/t3code-kit:latest'])
        self.assertFalse(any(x[0] == 'run' for x in calls))
        copied = [x[1] for x in calls if x[0] == 'cp']
        self.assertEqual(len(copied), 4)
        self.assertFalse(any('dot_claude' in x or 'private_config' in x for x in copied))
        self.assertIn('owner/repo', calls[-1])

    def test_agent_kit_reference_and_resource_options_are_preserved(self):
        kit = 'docker.io/docker/sbx-kit-codex:0.155.1'
        result = self.run_manager('create','my-project','owner/repo',kit,'true','--','--memory','8g')
        self.assertEqual(result.returncode,0,result.stderr)
        create = next(x for x in self.calls() if x[0]=='create')
        self.assertEqual(create[1],kit)
        self.assertEqual(create[-2:],['--memory','8g'])

    def test_invalid_inputs_never_create(self):
        cases = [
            ('create','x','owner/repo','claude'),
            ('create','my-project','owner/..','claude'),
            ('create','my-project','owner/repo;whoami','claude'),
            ('create','my-project','owner/repo','claude','yes'),
            ('create','my-project','owner/repo','claude','--','--mount','/Users/jai:/work'),
            ('create','my-project','owner/repo','claude','--','.'),
            ('check','my-project','extra'),
            ('serve','my-project'),
        ]
        for args in cases:
            with self.subTest(args=args):
                self.assertNotEqual(self.run_manager(*args).returncode,0)
        self.assertFalse(any(x[0]=='create' for x in self.calls()))

    def test_existing_sandbox_is_preserved(self):
        self.env['EXISTING']='other\nmy-project'
        self.assertNotEqual(self.run_manager('create','my-project','owner/repo','claude').returncode,0)
        self.assertEqual(self.calls(),[['ls','-q']])

    def test_failed_create_never_copies_or_deletes(self):
        self.env['FAIL_CREATE']='1'
        self.assertNotEqual(self.run_manager('create','my-project','owner/repo','claude').returncode,0)
        self.assertEqual([x[0] for x in self.calls()],['ls','create'])

    def test_refresh_refuses_unmanaged_sandbox(self):
        self.env['UNMANAGED']='1'
        self.assertNotEqual(self.run_manager('refresh','my-project','owner/repo').returncode,0)
        self.assertEqual(len(self.calls()),1)

    def test_check_uses_managed_sandbox_and_noninteractive_ssh(self):
        ssh = self.bin / 'ssh'
        ssh.write_text('''#!/usr/bin/env python3
import json, os, sys
with open(os.environ['MOCK_LOG'],'a') as f: f.write(json.dumps(['ssh',*sys.argv[1:]])+'\\n')
sys.stdin.read()
sys.exit(int(os.environ.get('SSH_FAIL','0')))
''')
        ssh.chmod(0o755)
        result = self.run_manager('check','my-project')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(self.calls(),[
            ['exec','-u','1000','my-project','--','test','-f','/home/agent/.config/dotfiles/managed'],
            ['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','my-project.sbx','bash -s'],
        ])
        self.env['SSH_FAIL']='1'
        self.assertNotEqual(self.run_manager('check','my-project').returncode,0)

    def test_check_refuses_unmanaged_sandbox_before_ssh(self):
        self.env['UNMANAGED']='1'
        self.assertNotEqual(self.run_manager('check','my-project').returncode,0)
        self.assertEqual(len(self.calls()),1)

    def test_refresh_enables_t3_setup_without_mounting_or_starting_an_agent(self):
        result = self.run_manager('refresh','my-project','owner/repo')
        self.assertEqual(result.returncode,0,result.stderr)
        calls = self.calls()
        self.assertEqual(calls[0],['exec','-u','1000','my-project','--','test','-f','/home/agent/.config/dotfiles/managed'])
        policy = next(x for x in calls if x[0]=='policy')
        self.assertIn('registry.npmjs.org',policy[-1])
        self.assertFalse(any(x[0] in ('create','run','ports','rm') for x in calls))

    def test_guest_script_refuses_native_execution(self):
        result = subprocess.run(['bash',str(BOOTSTRAP)],env=self.env,capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('inside a Docker Sandbox',result.stderr)


class T3BootstrapTests(unittest.TestCase):
    def setUp(self):
        import sys
        self.python = sys.executable
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.bin = self.root/'bin'
        self.bin.mkdir()
        self.local = self.root/'.local/bin'
        self.local.mkdir(parents=True)
        self.env = dict(os.environ, HOME=str(self.root), PATH=f'{self.local}:{self.bin}')
        for key in ('HTTP_PROXY','HTTPS_PROXY','http_proxy','https_proxy'):
            self.env.pop(key,None)
        source = BOOTSTRAP.read_text()
        section = source[source.index('# T3 readiness'):source.index('# sbx sources this')]
        self.script = self.root/'t3-setup.sh'
        self.script.write_text('set -euo pipefail\n'+section)
        self.log = self.root/'npm.json'
        npm = self.bin/'npm'
        npm.write_text(f'#!{self.python}\n'+'''import json, os, pathlib, sys
root = pathlib.Path(os.environ['HOME'])
(root/'npm.json').write_text(json.dumps(sys.argv[1:]))
if os.environ.get('FAIL_NPM'): sys.exit(17)
binary = root/'.local/bin/t3'
binary.write_text('#!/bin/sh\\nexit 0\\n')
binary.chmod(0o755)
''')
        npm.chmod(0o755)
        self.bash = shutil.which(HOST_BASH)

    def setup_t3(self):
        return subprocess.run([self.bash,str(self.script)],env=self.env,capture_output=True,text=True)

    def test_installs_missing_t3_in_guest_home_with_proxy(self):
        self.env.update(HTTP_PROXY='http://proxy.invalid:3128',HTTPS_PROXY='http://secure-proxy.invalid:3128')
        result = self.setup_t3()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(self.log.read_text()),[
            'install','--global','--prefix',str(self.root/'.local'),
            '--proxy','http://proxy.invalid:3128',
            '--https-proxy','http://secure-proxy.invalid:3128','t3@latest',
        ])
        self.log.unlink()
        self.assertEqual(self.setup_t3().returncode,0)
        self.assertFalse(self.log.exists())

    def test_http_proxy_also_supplies_https_fallback(self):
        self.env['HTTP_PROXY']='http://proxy.invalid:3128'
        self.assertEqual(self.setup_t3().returncode,0)
        args = json.loads(self.log.read_text())
        self.assertEqual(args[args.index('--https-proxy')+1],self.env['HTTP_PROXY'])

    def test_existing_broken_t3_fails_without_reinstalling(self):
        binary = self.local/'t3'
        binary.write_text('#!/bin/sh\nexit 19\n')
        binary.chmod(0o755)
        self.assertEqual(self.setup_t3().returncode,19)
        self.assertFalse(self.log.exists())

    def test_install_failure_is_not_reported_as_ready(self):
        self.env['FAIL_NPM']='1'
        self.assertEqual(self.setup_t3().returncode,17)
        self.assertFalse((self.local/'t3').exists())


class GitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        home = self.root/'home'
        home.mkdir()
        self.bin = self.root/'bin'
        self.bin.mkdir()
        self.env = dict(os.environ, HOME=str(home), PATH=f'{self.bin}:{os.environ["PATH"]}', GIT_CONFIG_NOSYSTEM='1')
        self.env.pop('GIT_CONFIG_GLOBAL',None)
        self.git('config','--global','user.name','Test')
        self.git('config','--global','user.email','test@example.invalid')
        remotes = self.root/'remotes'
        (remotes/'owner').mkdir(parents=True)
        seed = self.root/'seed'
        self.git('init','-b','trunk',str(seed))
        (seed/'README').write_text('base\n')
        self.git('-C',str(seed),'add','README')
        self.git('-C',str(seed),'commit','-m','initial')
        self.git('clone','--bare',str(seed),str(remotes/'owner/repo.git'))
        self.git('init','--bare',str(remotes/'owner/empty.git'))
        self.git('config','--global',f'url.{remotes.as_uri()}/.insteadOf','https://github.com/')
        source=BOOTSTRAP.read_text()
        start=source.index('if [[ ! -e $workspace/.git ]]')
        end=source.index('# Task ownership')
        self.script=self.root/'repo-setup.sh'
        self.script.write_text('set -euo pipefail\nworkspace=$1\nrepo=$2\n'+source[start:end])
        self.workspace=self.root/'workspace'

    def git(self,*args,check=True):
        return subprocess.run(['git',*args],env=self.env,capture_output=True,text=True,check=check)

    def setup_repo(self,repo='owner/repo'):
        return subprocess.run(['bash',str(self.script),str(self.workspace),repo],env=self.env,capture_output=True,text=True)

    def test_non_main_default_and_linked_worktree_hook(self):
        result=self.setup_repo()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(self.git('-C',str(self.workspace),'branch','--show-current').stdout.strip(),'trunk')
        linked=self.root/'task'
        self.git('-C',str(self.workspace),'worktree','add','-b','agent/test',str(linked),'origin/trunk')
        self.assertTrue((linked/'.git').is_file())
        hook=self.git('-C',str(linked),'rev-parse','--path-format=absolute','--git-path','hooks/pre-commit').stdout.strip()
        self.assertEqual(Path(hook),self.workspace/'.git/hooks/pre-commit')
        self.assertEqual(self.git('-C',str(linked),'config','credential.https://github.com.helper').stdout.strip(),'!gh auth git-credential')
        (self.bin/'gitleaks').write_text('#!/bin/sh\nexit 42\n')
        (self.bin/'gitleaks').chmod(0o755)
        (linked/'README').write_text('changed\n')
        self.git('-C',str(linked),'add','README')
        self.assertNotEqual(self.git('-C',str(linked),'commit','-m','blocked',check=False).returncode,0)

    def test_refresh_preserves_dirty_files_and_project_hook(self):
        self.assertEqual(self.setup_repo().returncode,0)
        (self.workspace/'README').write_text('uncommitted\n')
        hook=self.workspace/'.git/hooks/pre-commit'
        hook.write_text('#!/bin/sh\nexit 23\n')
        self.assertEqual(self.setup_repo().returncode,0)
        self.assertEqual((self.workspace/'README').read_text(),'uncommitted\n')
        self.assertEqual(hook.read_text(),'#!/bin/sh\nexit 23\n')

    def test_wrong_repository_is_rejected(self):
        self.assertEqual(self.setup_repo().returncode,0)
        self.assertNotEqual(self.setup_repo('owner/other').returncode,0)

    def test_empty_repository_is_rejected(self):
        self.assertNotEqual(self.setup_repo('owner/empty').returncode,0)

    def test_nonempty_directory_is_preserved(self):
        self.workspace.mkdir()
        (self.workspace/'important').write_text('keep')
        self.assertNotEqual(self.setup_repo().returncode,0)
        self.assertEqual((self.workspace/'important').read_text(),'keep')


@unittest.skipUnless(shutil.which('chezmoi'), 'chezmoi integration needs its CLI')
class ChezmoiTests(unittest.TestCase):
    def test_apply_removes_only_retired_files_and_is_repeatable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            home = root/'home'
            home.mkdir()
            source = root/'source'
            shutil.copytree(ROOT, source, ignore=shutil.ignore_patterns('.git', '__pycache__'))
            retired = (ROOT/'.chezmoiremove').read_text().splitlines()
            keep = ['.codex/config.toml', '.codex/auth.json', '.claude/.credentials.json', '.ssh/config', '.config/nvim/local.lua', 'notes.md']
            for name in retired + keep:
                path = home/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('preserve' if name in keep else 'retired')
            retired_link = home/'.sbxenv.yaml'
            retired_link.unlink()
            retired_link.symlink_to(home/'notes.md')
            env = dict(os.environ, HOME=str(home))
            for key in ('CONFIG', 'DATA', 'CACHE', 'STATE'):
                env[f'XDG_{key}_HOME'] = str(root/key.lower())
            command = [shutil.which('chezmoi'), '--source', str(source), '--destination', str(home),
                       '--config', str(root/'chezmoi.toml'), '--persistent-state', str(root/'state.boltdb'),
                       '--cache', str(root/'cache'), '--force', '--no-tty', 'apply']
            for _ in range(2):
                result = subprocess.run(command, env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(any((home/name).exists() for name in retired))
            for name in keep:
                self.assertEqual((home/name).read_text(), 'preserve')
            self.assertFalse((home/'sandbox').exists())
            self.assertFalse((home/'tests').exists())
            self.assertTrue((home/'.local/share/navi/cheats/sandbox.cheat').is_file())
            self.assertTrue((home/'.gitconfig').is_file())


if __name__ == '__main__':
    unittest.main()
