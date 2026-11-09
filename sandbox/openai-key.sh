#!/usr/bin/env bash
# Temporary OpenAI app-key workaround. Removing this file restores Navi's Docker flow.
set -euo pipefail
usage='Usage: openai-key.sh set|remove SANDBOX'
[[ $# == 2 ]] || { echo "$usage" >&2; exit 1; }
action=$1 sandbox=$2
case $action in set | remove) ;; *) echo "$usage" >&2; exit 1 ;; esac
[[ $sandbox =~ ^[a-zA-Z0-9][a-zA-Z0-9.-]{1,47}$ && $sandbox != default ]] || {
  echo 'Invalid sandbox name.' >&2; exit 1;
}
if [[ $action == set ]]; then
  sbx policy allow network --sandbox "$sandbox" api.openai.com:443
fi

# Only code crosses the process arguments. The real key is prompted inside the VM.
guest_code=$(cat <<'PY'
import getpass
import os
from pathlib import Path
import pwd
import shlex
import tempfile
import sys

action = sys.argv[1]
persistent = Path("/etc/sandbox-persistent.sh")
private = Path("/home/agent/.config/dotfiles/openai-api.sh")
begin = "# BEGIN dotfiles OpenAI app key"
end = "# END dotfiles OpenAI app key"
rules = [
    'case ",${NO_PROXY:-}," in *,api.openai.com,*) ;; *) export NO_PROXY="${NO_PROXY:+$NO_PROXY,}api.openai.com" ;; esac',
    'case ",${no_proxy:-}," in *,api.openai.com,*) ;; *) export no_proxy="${no_proxy:+$no_proxy,}api.openai.com" ;; esac',
]
original = persistent.read_text() if persistent.exists() else ""
lines = original.splitlines()
if lines.count(begin) != lines.count(end) or lines.count(begin) > 1:
    raise SystemExit("Incomplete OpenAI block; repair its markers before retrying.")
if begin in lines and lines.index(begin) > lines.index(end):
    raise SystemExit("Invalid OpenAI block order; repair its markers before retrying.")

# Adopt the earlier one-time setup, including its literal proxy guard lines.
legacy = [line for line in lines if line.startswith("export OPENAI_API_KEY=")]
is_direct = private.exists() or begin in lines
for line in legacy:
    values = shlex.split(line.partition("=")[2])
    is_direct |= bool(values and values[0].startswith("sk-"))
if action == "remove" and not is_direct:
    raise SystemExit(3)  # Let the host remove an older Docker custom secret instead.

clean = []
inside = False
for line in lines:
    if line == begin:
        inside = True
    elif line == end:
        inside = False
    elif not inside and line not in rules and not line.startswith("export OPENAI_API_KEY="):
        clean.append(line)

def atomic_write(path, content, mode, uid, gid):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".openai-key-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as stream:
            os.fchmod(stream.fileno(), mode)
            os.fchown(stream.fileno(), uid, gid)
            stream.write(content)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)

owner = persistent.stat() if persistent.exists() else None
mode, uid, gid = (owner.st_mode & 0o777, owner.st_uid, owner.st_gid) if owner else (0o644, 0, 0)
if action == "set":
    key = getpass.getpass("OpenAI app API key (saved only inside this sandbox): ").strip()
    if not key.startswith("sk-") or any(character.isspace() for character in key):
        raise SystemExit("Expected a real OpenAI API key; nothing changed.")
    agent = pwd.getpwuid(1000)
    previous = private.read_text() if private.exists() else None
    content = "export OPENAI_API_KEY=" + shlex.quote(key) + "\n" + "\n".join(rules) + "\n"
    atomic_write(private, content, 0o600, agent.pw_uid, agent.pw_gid)
    clean.extend([begin, f'. "{private}"', end])
    try:
        atomic_write(persistent, "\n".join(clean) + "\n", mode, uid, gid)
    except BaseException:
        if previous is None:
            private.unlink(missing_ok=True)
        else:
            atomic_write(private, previous, 0o600, agent.pw_uid, agent.pw_gid)
        raise
else:
    atomic_write(persistent, "\n".join(clean) + "\n", mode, uid, gid)
    private.unlink(missing_ok=True)
print("Saved OpenAI app key." if action == "set" else "Removed OpenAI app key and owned proxy exclusions.")
PY
)

status=0
sbx exec -it -u root "$sandbox" -- python3 -c "$guest_code" "$action" || status=$?
if [[ $status == 3 && $action == remove ]]; then
  sbx secret rm --sandbox "$sandbox" --host api.openai.com --env-name OPENAI_API_KEY
  sbx exec -u root "$sandbox" -- sh -c \
    'sed -i "/^export OPENAI_API_KEY=/d" /etc/sandbox-persistent.sh'
elif [[ $status != 0 ]]; then
  exit "$status"
fi
printf 'Restart existing app/T3 processes to load this change. No agent auth files were changed.\n'
