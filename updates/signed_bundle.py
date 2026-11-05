"""Only verified, explicitly allowed public release files can enter a publication ZIP."""
import hashlib
import io
import re
import zipfile
from pathlib import Path

from release import verify_envelope


def unpack(data, public_key, output):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        items = archive.infolist()
        names = [item.filename for item in items]
        channels = [name for name in names if re.fullmatch(r'channels/[a-z][a-z0-9-]{0,47}/[a-z][a-z0-9-]{0,47}/windows-x64\.json', name)]
        if len(channels) != 1 or len(names) != len(set(names)):
            raise ValueError('Expected a single signed channel and no duplicate files')
        if archive.getinfo(channels[0]).file_size > 65536:
            raise ValueError('Metadata exceeds limit')
        manifest = verify_envelope(archive.read(channels[0]), public_key)
        product, channel, revision = manifest['product'], manifest['channel'], manifest['revision']
        if (any(not isinstance(v, str) or not re.fullmatch('[a-z][a-z0-9-]{0,47}', v) for v in (product, channel))
                or type(revision) is not int or not 1 <= revision <= 2147483647
                or manifest['platform'] != 'windows-x64' or manifest['filename'] != 'client-windows-x64.exe'):
            raise ValueError('Invalid signed release identity')
        prefix = f'releases/{product}/{channel}/{revision}/'
        expected = {f'channels/{product}/{channel}/windows-x64.json', prefix + 'windows-x64.json',
                    prefix + 'client-windows-x64.exe', prefix + 'provenance.json'}
        if set(names) != expected:
            raise ValueError('Bundle contains unexpected files')
        for item in items:
            limit = 512 * 1024 * 1024 if item.filename.endswith('.exe') else 128 * 1024
            if not 0 < item.file_size <= limit:
                raise ValueError('Bundle file exceeds limit')
        binary = archive.read(prefix + 'client-windows-x64.exe')
        if len(binary) != manifest['size'] or hashlib.sha256(binary).hexdigest() != manifest['sha256']:
            raise ValueError('Installer does not match signed metadata')
        if archive.read(prefix + 'windows-x64.json') != archive.read(channels[0]):
            raise ValueError('Release and channel metadata differ')
        output.mkdir(parents=True, exist_ok=False)
        for name in names:
            target = output / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(name))
        return manifest


def pack(directory, public_key):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(directory.rglob('*')):
            if path.is_file():
                archive.write(path, path.relative_to(directory).as_posix())
    data = buffer.getvalue()
    import tempfile
    with tempfile.TemporaryDirectory() as temporary:
        unpack(data, public_key, Path(temporary) / 'verified')
    return data
