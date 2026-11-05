"""Add a ready installer to the download page without enabling automatic updates."""
import argparse
import fcntl
import hashlib
import os
from pathlib import Path
import shutil
import uuid

from download_catalog import update

EXTENSIONS = {'windows-x64': {'.exe'}, 'windows-x86': {'.exe'},
              'linux-x64': {'.deb', '.AppImage'}, 'linux-arm64': {'.deb', '.AppImage'},
              'macos-x64': {'.dmg'}, 'macos-arm64': {'.dmg'}}


def publish(root, source, platform, version):
    if platform not in EXTENSIONS or source.suffix not in EXTENSIONS[platform] or not version.strip():
        raise ValueError('Choose a supported platform, installer extension and version')
    if not source.is_file() or not 0 < source.stat().st_size <= 512 * 1024 * 1024:
        raise ValueError('Expected an installer of at most 512 MB')
    root.mkdir(parents=True, exist_ok=True)
    with (root / '.publish.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        folder = root / 'downloads'
        folder.mkdir(exist_ok=True)
        folder.chmod(0o755)
        temporary = folder / ('.incoming-' + uuid.uuid4().hex)
        try:
            shutil.copyfile(source, temporary)
            with temporary.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            destination = folder / f'StatusDesk-{platform}-{digest[:16]}{source.suffix}'
            temporary.chmod(0o644)
            os.replace(temporary, destination)
            update(root, platform, url='/client/downloads/' + destination.name, version=version)
        finally:
            if temporary.exists():
                temporary.unlink()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--file', type=Path, required=True)
    parser.add_argument('--platform', choices=EXTENSIONS, required=True)
    parser.add_argument('--version', required=True)
    args = parser.parse_args()
    publish(args.root, args.file, args.platform, args.version)
