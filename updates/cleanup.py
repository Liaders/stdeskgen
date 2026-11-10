"""Plan and remove only obsolete managed payloads; metadata is never removed."""
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


def safe_file(root, relative):
    if root.is_symlink() or (hasattr(root, 'is_junction') and root.is_junction()):
        raise ValueError('Linked cleanup root')
    root = root.resolve(strict=True)
    path = root / relative
    if not relative or Path(relative).is_absolute() or '..' in Path(relative).parts:
        raise ValueError('Unsafe cleanup path')
    if not path.resolve(strict=True).is_relative_to(root):
        raise ValueError('Cleanup path escapes catalog')
    for part in (path, *path.parents):
        if part == root: break
        if part.is_symlink() or (hasattr(part, 'is_junction') and part.is_junction()):
            raise ValueError('Linked cleanup path')
    if not path.is_file(): raise ValueError('Expected a regular file')
    return path


def plan(root, relatives, protected=()):
    items = []
    for relative in sorted(set(relatives)):
        path = safe_file(root, relative)
        stat = path.stat()
        items.append({'path': relative, 'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns})
    token = hashlib.sha256(json.dumps([items, sorted(protected)], sort_keys=True).encode()).hexdigest()
    return {'items': items, 'bytes': sum(i['size'] for i in items), 'token': token}


def remove(root, current, token):
    if not isinstance(token, str) or current['token'] != token:
        raise ValueError('Список изменился. Просмотрите и подтвердите удаление заново.')
    # Validate the complete set before the first unlink; never recursively delete.
    paths = [safe_file(root, item['path']) for item in current['items']]
    for path in paths: path.unlink()
    return {'deleted': len(paths), 'bytes': current['bytes']}


def server_plan(root):
    protected = set()
    catalog = json.loads(safe_file(root, 'downloads.json').read_text(encoding='utf-8'))
    if catalog.get('schema') != 1 or not isinstance(catalog.get('items'), dict):
        raise ValueError('Unsupported download catalog')
    for item in catalog['items'].values():
        for key in ('url', 'zip_url'):
            if key not in item: continue
            url = urlsplit(item[key])
            if url.scheme or url.netloc or not url.path.startswith('/client/'):
                raise ValueError('Unsupported catalog URL; cleanup stopped')
            relative = unquote(url.path.removeprefix('/client/'))
            safe_file(root, relative)
            protected.add(relative)
    channels = root/'channels'
    if channels.exists():
        for path in channels.rglob('*.json'):
            metadata = json.loads(safe_file(root, path.relative_to(root).as_posix()).read_text(encoding='utf-8'))
            parts = [metadata[k] for k in ('product', 'channel', 'platform')]
            if any(not isinstance(p, str) or not re.fullmatch('[a-z][a-z0-9-]{0,47}', p) for p in parts):
                raise ValueError('Invalid channel identity')
            revision = metadata['revision']
            if type(revision) is not int or revision < 1: raise ValueError('Invalid revision')
            folder = Path('releases', *parts, str(revision))
            filename = metadata['filename']
            if Path(filename).name != filename: raise ValueError('Invalid channel filename')
            safe_file(root, (folder/filename).as_posix())
            protected.update(p.relative_to(root).as_posix() for p in (root/folder).iterdir() if p.is_file())
    candidates = []
    for directory in ('downloads', 'releases'):
        for path in (root/directory).rglob('*'):
            if not path.is_file(): continue
            relative = path.relative_to(root).as_posix()
            managed = (directory == 'downloads' and re.fullmatch(r'downloads/StatusDesk-[a-z0-9-]+-[a-f0-9]{16}\.(exe|zip|apk|deb|AppImage|dmg)', relative)) or (
                directory == 'releases' and re.fullmatch(r'releases/[a-z0-9-]+/[a-z0-9-]+/windows-(x64|x86)/[0-9]+/client-windows-(x64|x86)\.(exe|zip)', relative))
            if managed and relative not in protected: candidates.append(relative)
    return plan(root, candidates, protected)


def server_main(token=None):
    import fcntl
    root = Path('/srv/stdesk-updates/public')
    with (root/'.publish.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        current = server_plan(root)
        return remove(root, current, token) if token is not None else current
