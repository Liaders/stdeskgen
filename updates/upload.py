"""Deploy a prepared bundle via SSH with host key verification."""
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
import uuid


def upload(bundle):
    host = os.environ['STDESK_UPDATE_HOST']
    user = os.environ['STDESK_UPDATE_USER']
    if not re.fullmatch('[A-Za-z0-9.-]+', host) or not re.fullmatch('[a-z_][a-z0-9_-]*', user):
        raise ValueError('Invalid SSH host/user')
    with tempfile.TemporaryDirectory() as temporary:
        key = Path(temporary) / 'key'
        hosts = Path(temporary) / 'known_hosts'
        key.write_text(os.environ['STDESK_UPDATE_SSH_KEY'] + '\n', encoding='utf-8')
        key.chmod(0o600)
        hosts.write_text(os.environ['STDESK_UPDATE_KNOWN_HOSTS'] + '\n', encoding='utf-8')
        options = ['-i', str(key), '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes',
                   '-o', 'StrictHostKeyChecking=yes', '-o', f'UserKnownHostsFile={hosts}']
        remote = user + '@' + host
        path = '/srv/stdesk-updates/incoming/' + uuid.uuid4().hex
        subprocess.run(['ssh', *options, remote, 'mkdir -m 700 ' + shlex.quote(path)], check=True)
        subprocess.run(['scp', *options, '-r', str(bundle) + '/.', remote + ':' + path + '/'], check=True)
        command = ('python3 /srv/stdesk-updates/bin/deploy.py --bundle ' + shlex.quote(path)
                   + ' --root /srv/stdesk-updates/public --public-key-file /srv/stdesk-updates/public-key.hex')
        subprocess.run(['ssh', *options, remote, command], check=True)


if __name__ == '__main__':
    import sys
    upload(Path(sys.argv[1]))
