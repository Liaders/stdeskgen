"""Download only installer artifacts and receipts; never execute archive contents."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import struct
import threading
import zipfile

from django.conf import settings

_lock = threading.Lock()
EXTENSIONS = {'.exe', '.msi', '.deb', '.rpm', '.AppImage', '.dmg', '.flatpak'}


def library_root():
    return Path(settings.BASE_DIR) / 'downloads'


def detect_platform(path, artifact=''):
    if path.suffix in ('.exe', '.msi'):
        if path.suffix == '.exe':
            with path.open('rb') as stream:
                if stream.read(2) != b'MZ':
                    raise ValueError('Invalid Windows executable')
                stream.seek(0x3c)
                stream.seek(struct.unpack('<I', stream.read(4))[0])
                header = stream.read(6)
            if header == b'PE\0\0\x64\x86': return 'windows-x64'
            if header == b'PE\0\0\x4c\x01': return 'windows-x86'
            raise ValueError('Unsupported EXE architecture')
        return 'windows-x86' if 'x86' in artifact and 'x86_64' not in artifact and 'x64' not in artifact else 'windows-x64'
    text = (artifact + ' ' + path.name).lower()
    arm = 'arm64' in text or 'aarch64' in text
    if path.suffix == '.dmg': return 'macos-arm64' if arm else 'macos-x64'
    if path.suffix in ('.deb', '.rpm', '.AppImage', '.flatpak'):
        return 'linux-arm64' if arm else 'linux-x64'
    raise ValueError('Unsupported installer format')


def download_build(record, session, request):
    from .local_build import LocalBuildError
    with _lock:
        destination = library_root() / record['id']
        marker = destination / 'library.json'
        if marker.exists():
            record.update(download_status='completed', download_directory=str(destination))
            return
        artifacts = request(session, 'GET', f"/actions/runs/{record['run_id']}/artifacts", params={'per_page': 100})['artifacts']
        artifacts = [a for a in artifacts if a['name'].startswith('client-') and not a['expired']]
        if not artifacts:
            raise LocalBuildError('No installer artifacts available (they may have expired).')
        destination.mkdir(parents=True, exist_ok=True)
        entries = []
        for artifact in artifacts:
            name = artifact['name']
            if not name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in name):
                raise LocalBuildError('Invalid artifact name')
            folder = destination / name
            folder.mkdir(exist_ok=True)
            archive_path = folder / '.download.zip'
            try:
                with session.get(artifact['archive_download_url'], timeout=300, stream=True) as response:
                    response.raise_for_status()
                    count = 0
                    with archive_path.open('wb') as output:
                        for chunk in response.iter_content(1024 * 1024):
                            count += len(chunk)
                            if count > 2 * 1024**3: raise ValueError('Artifact exceeds 2 GB')
                            output.write(chunk)
                with zipfile.ZipFile(archive_path) as archive:
                    if sum(i.file_size for i in archive.infolist()) > 2 * 1024**3:
                        raise ValueError('Extracted artifact exceeds 2 GB')
                    for item in archive.infolist():
                        relative = PurePosixPath(item.filename)
                        if item.is_dir(): continue
                        if relative.is_absolute() or '..' in relative.parts or '\\' in item.filename or ':' in item.filename:
                            raise ValueError('Unsafe archive path')
                        if relative.suffix not in EXTENSIONS and relative.name != 'stdesk-update-build.json': continue
                        target = folder.joinpath(*relative.parts)
                        if not target.resolve().is_relative_to(destination.resolve()): raise ValueError('Unsafe extraction target')
                        target.parent.mkdir(parents=True, exist_ok=True)
                        temporary = target.with_name(target.name + '.part')
                        with archive.open(item) as source, temporary.open('wb') as output:
                            import shutil
                            shutil.copyfileobj(source, output)
                        temporary.replace(target)
                for path in folder.rglob('*'):
                    if path.is_file() and path.suffix in EXTENSIONS:
                        relative = path.relative_to(library_root()).as_posix()
                        with path.open('rb') as stream:
                            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
                        receipt_path = path.parent / 'stdesk-update-build.json'
                        receipt = json.loads(receipt_path.read_text(encoding='utf-8')) if receipt_path.exists() else None
                        entries.append({'id': hashlib.sha256(relative.encode()).hexdigest(), 'relative_path': relative,
                            'filename': path.name, 'platform': detect_platform(path, name), 'size': path.stat().st_size,
                            'sha256': digest, 'version': (receipt or {}).get('version') or record.get('app_version') or record.get('version', '1.5.0'),
                            'build_id': record['id'], 'run_id': record['run_id'], 'receipt': receipt})
            except Exception as exc:
                raise LocalBuildError('Could not download installer artifacts: ' + str(exc)) from exc
            finally:
                archive_path.unlink(missing_ok=True)
        if not entries: raise LocalBuildError('No supported installers found in artifacts.')
        temporary = marker.with_suffix('.tmp')
        temporary.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding='utf-8')
        temporary.replace(marker)
        record.update(download_status='completed', download_directory=str(destination))
        record.pop('download_error', None)


def library():
    entries = []
    for marker in library_root().glob('*/library.json'):
        try:
            entries.extend(json.loads(marker.read_text(encoding='utf-8')))
        except (OSError, ValueError):
            continue
    return sorted(entries, key=lambda item: item.get('run_id') or 0, reverse=True)


def find_installer(identifier):
    for entry in library():
        if entry['id'] == identifier:
            path = library_root() / entry['relative_path']
            if not path.resolve().is_relative_to(library_root().resolve()) or not path.is_file():
                raise ValueError('Installer is missing')
            return entry, path
    raise ValueError('Installer not found')
