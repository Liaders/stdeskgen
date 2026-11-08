#!/usr/bin/env python3
"""Restore backup-cortendesk.sh bundles onto a fresh Ubuntu server (Python 3.12+)."""
import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile
import time


def run(*args, capture=False):
    return subprocess.run(args, check=True, text=True,
                          stdout=subprocess.PIPE if capture else None).stdout


def verify_checksum(archive):
    expected = Path(str(archive) + '.sha256').read_text().split()[0].lower()
    if len(expected) != 64 or any(c not in '0123456789abcdef' for c in expected):
        raise ValueError('Invalid checksum file')
    with archive.open('rb') as stream:
        actual = hashlib.file_digest(stream, 'sha256').hexdigest()
    if expected != actual:
        raise ValueError('Archive checksum mismatch; restoration stopped')


def extract(archive, destination):
    """Reject escaping links/paths and special files, preserve Linux data ownership."""
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive) as source:
        members = source.getmembers()
        # Validate every member before extraction starts, including link targets.
        for member in members:
            if member.name.startswith('/'):
                raise ValueError('Absolute archive member rejected')
            tarfile.data_filter(member, str(destination))
        source.extractall(destination, members=members, filter='data')
        for member in reversed(members):
            path = destination / member.name
            if not path.exists() and not path.is_symlink():
                continue
            if os.geteuid() == 0:
                os.chown(path, member.uid, member.gid, follow_symlinks=False)
            if not path.is_symlink():
                os.chmod(path, member.mode & 0o777)


def copy_preserved(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    run('cp', '-a', '--', str(source), str(target))


def make_spec(original, image, mounts):
    host = original['HostConfig']
    if host.get('Privileged') or host.get('Devices') or host.get('NetworkMode') == 'host' or host.get('NetworkMode', '').startswith('container:'):
        raise ValueError('Special container privileges/network require manual restoration')
    bindings = host.get('PortBindings') or {}
    for entries in bindings.values():
        for entry in entries or []:
            if entry.get('HostIp', '') not in ('', '0.0.0.0', '::', '127.0.0.1', '::1'):
                raise ValueError('Old explicit host IP in port bindings requires manual adaptation')
    config = original['Config']
    result = {key: config[key] for key in ('Env', 'Cmd', 'Entrypoint', 'WorkingDir', 'User',
              'ExposedPorts', 'Healthcheck', 'Labels', 'StopSignal') if config.get(key) is not None}
    result['Image'] = image
    result['HostConfig'] = {
        'Binds': [str(path) + ':' + mount['Destination'] + (':ro' if not mount.get('RW', True) else ':rw')
                  for mount, path in mounts],
        'PortBindings': bindings,
        'RestartPolicy': host.get('RestartPolicy') or {'Name': 'unless-stopped'},
        'NetworkMode': 'bridge',
    }
    for key in ('CapAdd', 'CapDrop', 'SecurityOpt', 'ShmSize', 'Ulimits', 'ExtraHosts', 'Dns', 'Init'):
        if host.get(key) is not None:
            result['HostConfig'][key] = host[key]
    return result


class DockerConnection(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(120)
        self.sock.connect('/var/run/docker.sock')


def create_container(spec):
    connection = DockerConnection('localhost', timeout=120)
    try:
        connection.request('POST', '/containers/create?name=cortendesk',
                           json.dumps(spec), {'Content-Type': 'application/json'})
        response = connection.getresponse()
        body = response.read()
        if response.status != 201:
            raise RuntimeError('Docker container creation failed, HTTP ' + str(response.status))
        return json.loads(body)['Id']
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--activate', action='store_true', help='Start the container and enable restored Apache site')
    args = parser.parse_args()
    if os.geteuid() != 0 or sys.version_info < (3, 12):
        parser.error('Run with sudo python3 on Ubuntu 24.04+ (Python 3.12+)')
    os.umask(0o077)
    archive = args.archive.resolve(strict=True)
    for tool in ('docker', 'cp', 'apache2ctl', 'a2enmod', 'a2ensite', 'systemctl', 'ip'):
        if not shutil.which(tool):
            raise RuntimeError('Install prerequisite first: ' + tool)
    run('docker', 'info', capture=True)
    names = run('docker', 'ps', '-a', '--format', '{{.Names}}', capture=True).splitlines()
    if 'cortendesk' in names:
        raise RuntimeError('Container cortendesk already exists; refusing to overwrite it')
    site = Path('/etc/apache2/sites-available/desk.status16.ru.conf')
    updates = Path('/srv/stdesk-updates')
    certs = Path('/etc/letsencrypt')
    if site.exists() or site.is_symlink() or updates.exists() or updates.is_symlink():
        raise RuntimeError('Existing StatusDesk Apache site/update directory: use a fresh server')
    if certs.is_symlink() or (certs.exists() and any(certs.iterdir())):
        raise RuntimeError('Existing certificate data: manual merge required')
    enabled = Path('/etc/apache2/sites-enabled')
    if any(p.name not in ('000-default.conf', 'default-ssl.conf') for p in enabled.iterdir()):
        raise RuntimeError('Other enabled Apache sites found; manual configuration merge required')

    print('Verifying complete archive checksum...')
    verify_checksum(archive)
    root = Path(tempfile.mkdtemp(prefix='cortendesk-restore-', dir='/srv'))
    bundle = root / 'bundle'
    print('Extracting private migration bundle to:', root)
    extract(archive, bundle)
    original = json.loads((bundle/'container-inspect.json').read_text())[0]
    database = json.loads((bundle/'database-info.json').read_text())
    if database['driver'] != 'sqlite':
        raise RuntimeError('External database requires a separate restore procedure')
    addresses = json.loads(run('ip', '-j', '-4', 'addr', capture=True))
    for interface in addresses:
        for addr in interface.get('addr_info', []):
            if addr.get('scope') == 'global' and addr['local'] == '146.185.211.114':
                raise RuntimeError('Old public IP detected: do not restore onto the old server')
    if not (bundle/'docker-image.tar').is_file():
        raise RuntimeError('Saved Docker image missing')

    host = root/'host-reference'
    extract(bundle/'host-files.tar', host)
    saved_site = host/'etc/apache2/sites-available/desk.status16.ru.conf'
    if not saved_site.is_file():
        raise RuntimeError('Expected Apache site is missing from backup')
    for required in ('etc/letsencrypt', 'srv/stdesk-updates'):
        if not (host/required).is_dir():
            raise RuntimeError('Required host directory missing: ' + required)
    mapped = []
    seen = {}
    mount_sources = (bundle/'mount-sources.bin').read_bytes().split(b'\0')
    for index, raw in enumerate((value for value in mount_sources if value), 1):
        old = raw.decode()
        unpacked = root/'unpacked-mounts'/str(index)
        extract(bundle/'mounts'/('mount-'+str(index)+'.tar'), unpacked)
        source = unpacked/old.lstrip('/')
        if not source.exists() and not source.is_symlink():
            raise RuntimeError('Mount data is missing')
        if source.is_symlink():
            raise RuntimeError('Symlink mount source needs manual mapping')
        target = root/'data'/str(index)
        copy_preserved(source, target)
        seen[old] = target
    for mount in original['Mounts']:
        if mount['Type'] not in ('bind', 'volume') or mount['Source'] not in seen:
            raise RuntimeError('Unsupported or missing Docker mount')
        mapped.append((mount, seen[mount['Source']]))
    spec = make_spec(original, original['Image'], mapped)
    # This file includes secrets, so it stays root-readable in the private directory.
    (root/'container-create.json').write_text(json.dumps(spec, indent=2))
    print('Loading the saved Docker image (no internet download)...')
    run('docker', 'load', '-i', str(bundle/'docker-image.tar'))
    create_container(spec)
    extra = bundle/'extra-container-files'
    # Restore root-filesystem changes that are not part of the immutable image.
    # /data and /app/storage copies are only used when not covered by a restored mount.
    def covered(destination):
        return any(destination == m['Destination'] or destination.startswith(m['Destination'].rstrip('/')+'/')
                   for m, _ in mapped)
    if (extra/'data').exists() and not covered('/data'):
        run('docker', 'cp', '-a', str(extra/'data'), 'cortendesk:/data')
    if not covered('/app/storage'):
        run('docker', 'cp', '-a', str(extra/'storage')+'/.', 'cortendesk:/app/storage')
    if (extra/'.env').exists() and not covered('/app/.env'):
        run('docker', 'cp', '-a', str(extra/'.env'), 'cortendesk:/app/.env')
    db_path = database['sqlite_path']
    if not covered(db_path) and not ((extra/'data').exists() and db_path.startswith('/data/')):
        for suffix in ('', '-wal', '-shm'):
            source = extra/('database.sqlite'+suffix)
            if source.exists():
                run('docker', 'cp', '-a', str(source), 'cortendesk:'+db_path+suffix)

    copy_preserved(saved_site, site)
    if certs.exists():
        # An existing empty directory was accepted during preflight.
        run('cp', '-a', str(host/'etc/letsencrypt')+'/.', str(certs))
    else:
        copy_preserved(host/'etc/letsencrypt', certs)
    copy_preserved(host/'srv/stdesk-updates', updates)
    # Make required Apache modules available without copying old global OS config.
    run('a2enmod', 'ssl', 'proxy', 'proxy_http', 'proxy_wstunnel', 'headers', 'rewrite', 'substitute', 'http2')
    print('Restored data and a STOPPED container. Private restore directory:', root)
    print('Original compose/global Apache/cron files remain under host-reference for review.')
    if not args.activate:
        print('To activate: sudo docker start cortendesk; sudo a2ensite desk.status16.ru.conf')
        print('Then run sudo apache2ctl configtest and start/reload Apache after a successful check.')
        return
    run('docker', 'start', 'cortendesk')
    deadline = time.monotonic()+180
    while time.monotonic() < deadline:
        state = json.loads(run('docker', 'inspect', '-f', '{{json .State}}', 'cortendesk', capture=True))
        if not state.get('Running'):
            raise RuntimeError('Container exited; inspect private Docker logs before continuing')
        if state.get('Health', {}).get('Status') == 'healthy':
            break
        time.sleep(3)
    else:
        raise RuntimeError('Container not healthy within 180 seconds; Apache site not activated')
    run('a2ensite', 'desk.status16.ru.conf')
    try:
        run('apache2ctl', 'configtest')
    except subprocess.CalledProcessError:
        run('a2dissite', 'desk.status16.ru.conf')
        raise
    run('systemctl', 'enable', '--now', 'docker', 'apache2')
    run('systemctl', 'reload', 'apache2')
    print('Restored and started. Test the NEW IP with curl --resolve before changing DNS.')
    print('Do not apply old network settings. Configure cloud firewall and DNS separately.')
    print('Keep backup private. Reconfigure SSH publication/certbot renewal on the new host.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('RESTORE STOPPED:', type(error).__name__, str(error), file=sys.stderr)
        print('Existing data is not automatically deleted. Inspect the private restore directory before retrying.', file=sys.stderr)
        sys.exit(1)
