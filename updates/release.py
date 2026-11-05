"""Create and verify immutable signed update bundles. No private key is written to output."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import time

from nacl.signing import SigningKey, VerifyKey
from config import validate

MAX_FILE = 512 * 1024 * 1024


def verify_envelope(data, public_key):
    envelope = json.loads(data)
    payload = envelope['payload'].encode('utf-8')
    VerifyKey(bytes.fromhex(public_key)).verify(payload, bytes.fromhex(envelope['signature']))
    return json.loads(payload)


def windows_x64(path):
    with path.open('rb') as stream:
        if stream.read(2) != b'MZ':
            raise ValueError('Installer is not a Windows executable')
        stream.seek(0x3c)
        offset = struct.unpack('<I', stream.read(4))[0]
        stream.seek(offset)
        if stream.read(6) != b'PE\0\0\x64\x86':
            raise ValueError('Installer is not Windows x64')


def prepare(source, output, seed, app_name, version, run_id, commit):
    receipt = json.loads((source / 'stdesk-update-build.json').read_text(encoding='utf-8'))
    config = validate({key: receipt[key] for key in ('base_url', 'public_key', 'product', 'channel', 'revision')})
    if receipt.get('platform') != 'windows-x64' or receipt.get('schema') != 1:
        raise ValueError('Missing compatible build receipt')
    if not app_name.strip() or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?:[+-][0-9]+)?', version):
        raise ValueError('An app name and numeric display version are required')
    key = SigningKey(bytes.fromhex(seed))
    if key.verify_key.encode().hex() != config['public_key']:
        raise ValueError('Signing key does not match the key embedded in this build')
    candidates = list(source.glob('*.exe'))
    if len(candidates) != 1:
        raise ValueError('Expected exactly one packed EXE in the build artifact')
    binary = candidates[0]
    windows_x64(binary)
    if not 0 < binary.stat().st_size <= MAX_FILE:
        raise ValueError('Installer exceeds size limit')
    # App identity is recorded during compilation; it cannot be chosen at publication.
    if app_name != receipt.get('app_name') or version != receipt.get('version'):
        raise ValueError('Published app name/version must match the build receipt')
    relative = Path('releases') / config['product'] / config['channel'] / str(config['revision'])
    directory = output / relative
    directory.mkdir(parents=True, exist_ok=False)
    target = directory / 'client-windows-x64.exe'
    shutil.copyfile(binary, target)
    with target.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    payload = {'schema': 1, 'product': config['product'], 'channel': config['channel'],
               'revision': config['revision'], 'version': version, 'app_name': app_name,
               'platform': 'windows-x64', 'filename': target.name, 'size': target.stat().st_size,
               'sha256': digest, 'expires': int(time.time()) + 365 * 24 * 3600}
    raw = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    envelope = json.dumps({'payload': raw, 'signature': key.sign(raw.encode()).signature.hex()}, ensure_ascii=False).encode()
    verify_envelope(envelope, config['public_key'])
    (directory / 'windows-x64.json').write_bytes(envelope)
    channel = output / 'channels' / config['product'] / config['channel']
    channel.mkdir(parents=True, exist_ok=True)
    (channel / 'windows-x64.json').write_bytes(envelope)
    audit = {'run_id': run_id, 'commit': commit, 'build': receipt, 'release': payload}
    (directory / 'provenance.json').write_text(json.dumps(audit, indent=2) + '\n', encoding='utf-8')
    return payload


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--key-file', type=Path, required=True)
    args = parser.parse_args()
    receipt = json.loads((args.source / 'stdesk-update-build.json').read_text(encoding='utf-8'))
    from local_key import load
    release = prepare(args.source, args.output, load(args.key_file).encode().hex(),
                      receipt['app_name'], receipt['version'], args.run_id, args.commit)
    print(json.dumps(release, ensure_ascii=False))
