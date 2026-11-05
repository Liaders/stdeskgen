"""Prepare immutable HTTPS update packages without custom signing keys."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct

from config import validate

MAX_FILE = 512 * 1024 * 1024


def load_manifest(data):
    value = json.loads(data)
    expected = {'schema', 'product', 'channel', 'revision', 'version', 'app_name', 'platform', 'filename', 'size', 'sha256'}
    if not isinstance(value, dict) or set(value) != expected or value['schema'] != 2:
        raise ValueError('Expected update manifest schema 2 without signing keys')
    if value['platform'] not in ('windows-x64','windows-x86') or value['filename'] != 'client-' + value['platform'] + '.exe':
        raise ValueError('Unsupported update platform or filename')
    for field in ('product', 'channel'):
        if not isinstance(value[field], str) or not re.fullmatch('[a-z][a-z0-9-]{0,47}', value[field]):
            raise ValueError('Invalid update identity')
    if type(value['revision']) is not int or not 1 <= value['revision'] <= 2147483647:
        raise ValueError('Invalid update revision')
    if type(value['size']) is not int or not 0 < value['size'] <= MAX_FILE:
        raise ValueError('Invalid update size')
    if not isinstance(value['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', value['sha256']):
        raise ValueError('Invalid SHA-256')
    if not isinstance(value['app_name'], str) or not value['app_name'].strip():
        raise ValueError('Invalid application name')
    if not isinstance(value['version'], str) or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?:[+-][0-9]+)?', value['version']):
        raise ValueError('Invalid display version')
    return value


def windows_exe(path, platform):
    with path.open('rb') as stream:
        if stream.read(2) != b'MZ':
            raise ValueError('Installer is not a Windows executable')
        stream.seek(0x3c)
        offset = struct.unpack('<I', stream.read(4))[0]
        stream.seek(offset)
        machine = b'\x4c\x01' if platform == 'windows-x86' else b'\x64\x86'
        if stream.read(6) != b'PE\0\0' + machine:
            raise ValueError('Installer architecture does not match build receipt')


def prepare(source, output, app_name, version, run_id, commit):
    receipt = json.loads((source / 'stdesk-update-build.json').read_text(encoding='utf-8'))
    platform = receipt.get('platform')
    config = validate({key: receipt[key] for key in ('base_url', 'product', 'channel', 'revision')}, platform='windows-x86' if platform=='windows-x86' else 'windows')
    if platform not in ('windows-x64','windows-x86') or receipt.get('schema') != 2:
        raise ValueError('Missing compatible build receipt')
    if not app_name.strip() or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?:[+-][0-9]+)?', version):
        raise ValueError('An app name and numeric display version are required')
    candidates = list(source.glob('*.exe'))
    if len(candidates) != 1:
        raise ValueError('Expected exactly one packed EXE in the build artifact')
    binary = candidates[0]
    windows_exe(binary, platform)
    if not 0 < binary.stat().st_size <= MAX_FILE:
        raise ValueError('Installer exceeds size limit')
    # App identity is recorded during compilation; it cannot be chosen at publication.
    if app_name != receipt.get('app_name') or version != receipt.get('version'):
        raise ValueError('Published app name/version must match the build receipt')
    relative = Path('releases') / config['product'] / config['channel'] / platform / str(config['revision'])
    directory = output / relative
    directory.mkdir(parents=True, exist_ok=False)
    target = directory / ('client-' + platform + '.exe')
    shutil.copyfile(binary, target)
    with target.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    payload = {'schema': 2, 'product': config['product'], 'channel': config['channel'],
               'revision': config['revision'], 'version': version, 'app_name': app_name,
               'platform': platform, 'filename': target.name, 'size': target.stat().st_size,
               'sha256': digest}
    data = (json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + '\n').encode('utf-8')
    load_manifest(data)
    (directory / (platform + '.json')).write_bytes(data)
    channel = output / 'channels' / config['product'] / config['channel']
    channel.mkdir(parents=True, exist_ok=True)
    (channel / (platform + '.json')).write_bytes(data)
    audit = {'run_id': run_id, 'commit': commit, 'build': receipt, 'release': payload}
    (directory / 'provenance.json').write_text(json.dumps(audit, indent=2) + '\n', encoding='utf-8')
    return payload


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--commit', required=True)
    args = parser.parse_args()
    receipt = json.loads((args.source / 'stdesk-update-build.json').read_text(encoding='utf-8'))
    release = prepare(args.source, args.output,
                      receipt['app_name'], receipt['version'], args.run_id, args.commit)
    print(json.dumps(release, ensure_ascii=False))
