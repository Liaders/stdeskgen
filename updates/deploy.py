"""Publish an update bundle locally on the Apache host. Run as its deployment user."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import uuid

from release import load_manifest


def deploy(bundle, root, public_download=False):
    root.mkdir(parents=True, exist_ok=True)
    with (root / '.publish.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        channels = list((bundle / 'channels').glob('*/*/windows-*.json'))
        if len(channels) != 1:
            raise ValueError('Expected one channel per bundle')
        data = channels[0].read_bytes()
        manifest = load_manifest(data)
        product, channel, revision = manifest['product'], manifest['channel'], manifest['revision']
        platform = manifest['platform']
        import re
        if any(not re.fullmatch('[a-z][a-z0-9-]{0,47}', value) for value in (product, channel)) or type(revision) is not int or revision < 1:
            raise ValueError('Invalid release identity')
        relative = Path('releases') / product / channel / platform / str(revision)
        source = bundle / relative
        binary = source / manifest['filename']
        import hashlib
        with binary.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != manifest['sha256'] or binary.stat().st_size != manifest['size']:
            raise ValueError('Bundle binary does not match metadata')
        current = root / 'channels' / product / channel / (platform + '.json')
        if current.exists():
            previous = load_manifest(current.read_bytes())
            if revision == previous['revision'] and manifest == previous:
                published = root / relative / manifest['filename']
                with published.open('rb') as stream:
                    actual = hashlib.file_digest(stream, 'sha256').hexdigest()
                if actual != digest or published.stat().st_size != manifest['size']:
                    raise ValueError('Published file integrity mismatch')
                if channel == 'stable' or public_download:
                    from download_catalog import update
                    update(root, platform, url='/client/' + relative.as_posix() + '/' + manifest['filename'], version=manifest['version'])
                print(f'Already published {product}/{channel} revision {revision}')
                return
            if revision <= previous['revision']:
                raise ValueError('Revision must increase; old releases cannot be overwritten')
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        for directory in (root / 'releases', root / 'releases' / product, root / 'releases' / product / channel, target.parent):
            directory.chmod(0o755)
        staging = target.parent / ('.incoming-' + uuid.uuid4().hex)
        if target.exists():
            raise ValueError('Release already exists; use a new revision')
        staging.mkdir()
        staging.chmod(0o755)
        try:
            shutil.copyfile(binary, staging / binary.name)
            (staging / (platform + '.json')).write_bytes(data)
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
        if channel == 'stable' or public_download:
            from download_catalog import update
            update(root, platform, url='/client/' + relative.as_posix() + '/' + manifest['filename'], version=manifest['version'])
        print(f'Published {product}/{channel} revision {revision}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    deploy(args.bundle, args.root)
