"""Upload a ready installer using the operator's existing PuTTY key, then publish it."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import struct
import subprocess
import uuid

ROOT = Path(__file__).resolve().parents[1]
PLATFORMS = ('windows-x64', 'windows-x86', 'linux-x64', 'linux-arm64', 'macos-x64', 'macos-arm64')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--file', type=Path, required=True)
    parser.add_argument('--platform', choices=PLATFORMS, required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--receipt', type=Path)
    parser.add_argument('--config', type=Path, default=ROOT / '.local-publish.json')
    args = parser.parse_args()
    if args.receipt:
        metadata = json.loads(args.receipt.read_text(encoding='utf-8'))
        if metadata.get('schema') != 2 or metadata.get('platform') != args.platform or metadata.get('version') != args.version:
            raise ValueError('Auto-update requires the original receipt for this platform/version')
    config = json.loads(args.config.read_text(encoding='utf-8-sig'))
    host, user, port, key = config['host'], config['user'], config['port'], Path(config['key_file'])
    if not re.fullmatch('[A-Za-z0-9.-]+', host) or not re.fullmatch('[a-z_][a-z0-9_-]*', user) or type(port) is not int or not 1 <= port <= 65535:
        raise ValueError('Invalid SSH settings')
    source = args.file.resolve(strict=True)
    extensions = {'windows': {'.exe'}, 'linux': {'.deb', '.AppImage'}, 'macos': {'.dmg'}}
    if source.suffix not in extensions[args.platform.split('-')[0]] or not 0 < source.stat().st_size <= 512 * 1024 * 1024:
        raise ValueError('Choose the appropriate installer (up to 512 MB)')
    if not key.is_file() or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?:\.[0-9]+)?(?:[+-][0-9]+)?', args.version):
        raise ValueError('Missing PuTTY key file or invalid version')
    if args.platform.startswith('windows-'):
        with source.open('rb') as stream:
            if stream.read(2) != b'MZ':
                raise ValueError('Expected Windows EXE')
            stream.seek(0x3c)
            offset = struct.unpack('<I', stream.read(4))[0]
            stream.seek(offset)
            expected = b'PE\0\0' + (b'\x64\x86' if args.platform == 'windows-x64' else b'\x4c\x01')
            if stream.read(6) != expected:
                raise ValueError('EXE architecture does not match the selected platform')
    plink = shutil.which('plink') or 'C:/Program Files/PuTTY/plink.exe'
    pscp = shutil.which('pscp') or 'C:/Program Files/PuTTY/pscp.exe'
    connection = ['-batch', '-P', str(port), '-i', str(key)]
    target = user + '@' + host

    def remote(command):
        subprocess.run([plink, *connection, target, command], check=True)

    with source.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    staging = '/tmp/stdesk-publish-' + uuid.uuid4().hex
    installer = staging + '/installer' + source.suffix
    remote('set -e; sudo -n true; python3 -c "import sys; assert sys.version_info >= (3,11), \'Python 3.11+ required\'"; mkdir -m 700 ' + shlex.quote(staging))
    subprocess.run([pscp, *connection, str(source), target + ':' + installer], check=True)
    scripts = ('publish_download.py', 'download_catalog.py', 'deploy.py', 'release.py', 'config.py')
    for name in scripts:
        subprocess.run([pscp, *connection, str(Path(__file__).with_name(name)), target + ':' + staging + '/' + name], check=True)
    if args.receipt:
        subprocess.run([pscp, *connection, str(args.receipt.resolve()), target + ':' + staging + '/stdesk-update-build.json'], check=True)
    check = shlex.quote(digest + '  ' + installer)
    remote("printf '%s\\n' " + check + ' | sha256sum -c -')
    command = ('set -e; sudo -n install -d -m 755 /srv/stdesk-updates/bin; '
               + 'sudo -n install -m 644 ' + ' '.join(shlex.quote(staging + '/' + name) for name in scripts) + ' /srv/stdesk-updates/bin/; '
               + 'sudo -n python3 /srv/stdesk-updates/bin/publish_download.py --root /srv/stdesk-updates/public --file '
               + shlex.quote(installer) + ' --platform ' + shlex.quote(args.platform) + ' --version ' + shlex.quote(args.version))
    if args.receipt: command += ' --receipt ' + shlex.quote(staging + '/stdesk-update-build.json')
    remote(command)
    print(f'Published {args.platform}, version {args.version}. SHA-256: {digest}')
    print('Download page and automatic update use the same published file.' if args.receipt else 'Open https://desk.status16.ru/client/ to download. Automatic update channel is unchanged.')


if __name__ == '__main__':
    main()
