"""Publish a verified bundle locally on the Apache host. Run as its deployment user."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import uuid

from release import verify_envelope


def deploy(bundle, root, public_key):
    root.mkdir(parents=True, exist_ok=True)
    with (root / '.publish.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        channels = list((bundle / 'channels').glob('*/*/windows-x64.json'))
        if len(channels) != 1:
            raise ValueError('Expected one channel per bundle')
        data = channels[0].read_bytes()
        manifest = verify_envelope(data, public_key)
        product, channel, revision = manifest['product'], manifest['channel'], manifest['revision']
        import re
        if any(not re.fullmatch('[a-z][a-z0-9-]{0,47}', value) for value in (product, channel)) or type(revision) is not int or revision < 1:
            raise ValueError('Invalid release identity')
        relative = Path('releases') / product / channel / str(revision)
        source = bundle / relative
        binary = source / 'client-windows-x64.exe'
        import hashlib
        with binary.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != manifest['sha256'] or binary.stat().st_size != manifest['size']:
            raise ValueError('Bundle binary does not match signed metadata')
        current = root / 'channels' / product / channel / 'windows-x64.json'
        if current.exists():
            previous = verify_envelope(current.read_bytes(), public_key)
            if revision <= previous['revision']:
                raise ValueError('Revision must increase; old releases cannot be overwritten')
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        for directory in (root / 'releases', root / 'releases' / product, target.parent):
            directory.chmod(0o755)
        staging = target.parent / ('.incoming-' + uuid.uuid4().hex)
        if target.exists():
            raise ValueError('Release already exists; use a new revision')
        staging.mkdir()
        staging.chmod(0o755)
        try:
            shutil.copyfile(binary, staging / binary.name)
            (staging / 'windows-x64.json').write_bytes(data)
            shutil.copyfile(source / 'provenance.json', staging / 'provenance.json')
            for file in staging.iterdir():
                file.chmod(0o644)
            os.rename(staging, target)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
        current.parent.mkdir(parents=True, exist_ok=True)
        for directory in (root / 'channels', root / 'channels' / product, current.parent):
            directory.chmod(0o755)
        temporary = current.with_suffix('.' + uuid.uuid4().hex + '.tmp')
        temporary.write_bytes(data)
        temporary.chmod(0o644)
        os.replace(temporary, current)
        print(f'Published {product}/{channel} revision {revision}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--public-key-file', type=Path, required=True)
    args = parser.parse_args()
    deploy(args.bundle, args.root, args.public_key_file.read_text().strip())
