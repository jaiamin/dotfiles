"""Boundary tests use a fake sbx; Git behavior uses real local repositories."""
import json
import os
from pathlib import Path
import shutil
import sys
import io
import tarfile
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

    def test_builtin_agents_use_v3_t3_without_workspace_mount_or_agent_launch(self):
        for agent in ('codex','claude','opencode'):
            with self.subTest(agent=agent):
                if self.log.exists():
                    self.log.unlink()
                result = self.run_manager('create','my-project','owner/repo',agent,'false')
                self.assertEqual(result.returncode,0,result.stderr)
                calls = self.calls()
                create = next(x for x in calls if x[0]=='create')
                self.assertEqual(create,[
                    'create',agent,'--name','my-project','--cpus','4','--memory','4g',
                    '--skills','readonly','--kit','docker.io/sbx/t3code:latest',
                ])
                self.assertFalse(any(x[0]=='run' for x in calls))
                copied = [x[1] for x in calls if x[0]=='cp']
                self.assertEqual(len(copied),4)
                self.assertFalse(any('dot_claude' in x or 'private_config' in x for x in copied))
                self.assertIn('owner/repo',calls[-1])

    def test_agent_kit_reference_and_resource_options_are_preserved(self):
        kit = 'docker.io/sbx/codex:latest'
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


def node_setup_source():
    source = BOOTSTRAP.read_text()
    start = source.index('ensure_node() (')
    end = source.index('\nif [[ ',start)
    return source[start:end]


class NodeBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.bin = self.root/'bin'
        self.bin.mkdir()
        self.local = self.root/'.local/bin'
        self.local.mkdir(parents=True)
        self.env = dict(os.environ, HOME=str(self.root), PATH=f'{self.local}:{self.bin}',
                        GIT_CONFIG_NOSYSTEM='1',TEST_ARCH='x86_64')
        self.env.pop('GIT_CONFIG_GLOBAL',None)
        self.bash = shutil.which(HOST_BASH)
        for name in ('awk','mktemp','mkdir','tar','gzip','ln','rm'):
            (self.bin/name).symlink_to(shutil.which(name))
        self.tool('sha256sum',f'#!{sys.executable}\n'+'''import hashlib, pathlib, sys
digest,name=pathlib.Path(sys.argv[-1]).read_text().split()
sys.exit(0 if hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest()==digest else 1)
''')
        self.tool('uname','#!/bin/sh\nif [ "$1" = -m ]; then echo "$TEST_ARCH"; else echo Linux; fi\n')
        self.fixtures = self.root/'fixtures'
        self.fixtures.mkdir()
        for arch in ('x64','arm64'):
            filename = f'node-v24.22.2-linux-{arch}.tar.gz'
            with tarfile.open(self.fixtures/filename,'w:gz') as archive:
                for tool in ('node','npm','npx'):
                    content = ('#!/bin/sh\nif [ "$1" = -p ]; then echo 24; else echo v24.22.2; fi\n'
                               if tool=='node' else '#!/bin/sh\necho 11.0.0\n').encode()
                    entry = tarfile.TarInfo(f'node-v24.22.2-linux-{arch}/bin/{tool}')
                    entry.mode = 0o755
                    entry.size = len(content)
                    archive.addfile(entry,io.BytesIO(content))
        self.tool('curl',f'#!{sys.executable}\n'+'''import hashlib, json, os, pathlib, shutil, sys
root=pathlib.Path(os.environ['HOME'])
args=sys.argv[1:]
with (root/'downloads.jsonl').open('a') as log: log.write(json.dumps(args)+'\\n')
if os.environ.get('FAIL_DOWNLOAD'): sys.exit(22)
url=args[0] if not args[0].startswith('-') else args[1]
dest=pathlib.Path(args[args.index('-o')+1])
arch='arm64' if os.environ.get('TEST_ARCH') in ('arm64','aarch64') else 'x64'
name=f'node-v24.22.2-linux-{arch}.tar.gz'
fixture=root/'fixtures'/name
if url.endswith('SHASUMS256.txt'):
    digest='0'*64 if os.environ.get('BAD_CHECKSUM') else hashlib.sha256(fixture.read_bytes()).hexdigest()
    dest.write_text(f'{digest}  {name}\\n')
else: shutil.copyfile(fixture,dest)
''')
        self.script=self.root/'node-setup.sh'
        self.script.write_text('set -euo pipefail\n'+node_setup_source()+'\nensure_node\n')

    def tool(self,name,content):
        path=self.bin/name
        if path.is_symlink():
            path.unlink()
        path.write_text(content)
        path.chmod(0o755)

    def run_setup(self):
        return subprocess.run([self.bash,str(self.script)],env=self.env,capture_output=True,text=True)

    def test_missing_node_installs_checked_runtime_for_both_architectures(self):
        for arch in ('x86_64','aarch64'):
            with self.subTest(arch=arch):
                for tool in self.local.iterdir():
                    tool.unlink()
                self.env['TEST_ARCH']=arch
                result=self.run_setup()
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertIn('v24.22.2',result.stdout)
                self.assertTrue((self.local/'node').is_symlink())
                before=(self.root/'downloads.jsonl').read_text()
                self.assertEqual(self.run_setup().returncode,0)
                self.assertEqual((self.root/'downloads.jsonl').read_text(),before)

    def test_compatible_runtime_is_preserved(self):
        self.tool('node','#!/bin/sh\necho 22\n')
        for tool in ('npm','npx'):
            self.tool(tool,'#!/bin/sh\nexit 0\n')
        self.assertEqual(self.run_setup().returncode,0)
        self.assertFalse((self.root/'downloads.jsonl').exists())
        self.assertFalse((self.local/'node').exists())

    def test_missing_npm_repairs_runtime(self):
        self.tool('node','#!/bin/sh\necho 24\n')
        result=self.run_setup()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue((self.local/'npm').is_symlink())

    def test_checksum_failure_never_installs_runtime(self):
        self.env['BAD_CHECKSUM']='1'
        self.assertNotEqual(self.run_setup().returncode,0)
        self.assertFalse((self.local/'node').exists())

    def test_download_failure_never_installs_runtime(self):
        self.env['FAIL_DOWNLOAD']='1'
        self.assertNotEqual(self.run_setup().returncode,0)
        self.assertFalse((self.local/'node').exists())

    def exercise_full_bootstrap(self,marked):
        for name in ('cat','install','chmod','dirname','grep','tee','git','env','touch'):
            (self.bin/name).symlink_to(shutil.which(name))
        self.tool('id','#!/bin/sh\necho 1000\n')
        self.tool('sudo',f'#!{sys.executable}\nimport os,sys\nos.execvpe(sys.argv[1],sys.argv[1:],os.environ)\n')
        self.tool('apt-get','#!/bin/sh\nexit 0\n')
        for name in ('uv','pnpm','gitleaks'):
            self.tool(name,'#!/bin/sh\nexit 0\n')
        self.tool('t3','#!/bin/sh\nexec node --version\n')
        def git(*args):
            return subprocess.run([str(self.bin/'git'),*args],env=self.env,
                                  capture_output=True,text=True,check=True)
        git('config','--global','user.name','Test')
        git('config','--global','user.email','test@example.invalid')
        seed=self.root/'seed'
        git('init','-b','trunk',str(seed))
        (seed/'README').write_text('initial\n')
        git('-C',str(seed),'add','README')
        git('-C',str(seed),'commit','-m','initial')
        remotes=self.root/'remotes'
        (remotes/'owner').mkdir(parents=True)
        git('clone','--bare',str(seed),str(remotes/'owner/repo.git'))
        git('config','--global',f'url.{remotes.as_uri()}/.insteadOf','https://github.com/')
        source=self.root/'source'
        source.mkdir()
        for name in ('base.md','AGENTS.md','gitignore'):
            (source/name).write_text('fixture\n')
        # Map only sandbox filesystem constants into this disposable test home.
        script=source/'bootstrap.sh'
        script.write_text(BOOTSTRAP.read_text().replace('/home/agent',str(self.root))
                          .replace('/etc/sandbox-persistent.sh',str(self.root/'persistent.sh')))
        if marked:
            state=self.root/'.local/state/dotfiles'
            state.mkdir(parents=True)
            (state/'tools-v1').touch()
        result=subprocess.run([self.bash,str(script),'owner/repo','false','Test','test@example.invalid'],
                              env=self.env,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        workspace=self.root/'workspace'
        self.assertEqual(git('-C',str(workspace),'config','--get','remote.origin.url').stdout.strip(),
                         'https://github.com/owner/repo.git')
        self.assertEqual((workspace/'README').read_text(),'initial\n')
        self.assertTrue((self.local/'node').exists())
        self.assertIn('Ready:',result.stdout)

    def test_fresh_image_without_node_reaches_repository_clone(self):
        self.exercise_full_bootstrap(marked=False)

    def test_refresh_with_old_tools_marker_repairs_node_and_clones(self):
        self.exercise_full_bootstrap(marked=True)


@unittest.skipUnless(os.environ.get('TEST_NODE_DOWNLOAD')=='1','real Linux runtime download is CI-only')
class NodeDownloadTests(unittest.TestCase):
    def test_official_archive_supplies_working_node_npm_and_npx(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve()
            bin_dir=root/'bin'
            bin_dir.mkdir()
            for name in ('awk','mktemp','mkdir','tar','gzip','sha256sum','ln','rm','curl','uname'):
                (bin_dir/name).symlink_to(shutil.which(name))
            env=dict(os.environ,HOME=str(root),PATH=f'{root}/.local/bin:{bin_dir}')
            script=root/'setup.sh'
            script.write_text('set -euo pipefail\n'+node_setup_source()+'\nensure_node\n')
            result=subprocess.run([shutil.which(HOST_BASH),str(script)],env=env,
                                  capture_output=True,text=True,timeout=180)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('v24.22.2',result.stdout)
            self.assertTrue((root/'.local/bin/npm').exists())


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
