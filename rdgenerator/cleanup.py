"""Preview-driven cleanup using the existing local library and SSH settings."""
import base64
import json
from pathlib import Path
import re
import shlex
import subprocess

from django.conf import settings
from updates.cleanup import plan, remove, safe_file
from updates.publish_from_windows import putty_connection
from .build_downloads import library_root, library, _lock
from .publication_selection import PLATFORMS


def local_plan():
    root = library_root()
    if not root.exists(): return plan_empty()
    groups = {}
    for item in library():
        if item.get('platform') not in PLATFORMS: continue
        version = item.get('version', '')
        if not re.fullmatch(r'\d+\.\d+\.\d+(?:\.\d+)?', version): continue
        relative = item['relative_path']
        if not (root/relative).exists(): continue
        path = safe_file(root, relative)
        if path.suffix not in ('.exe', '.deb', '.AppImage', '.dmg', '.apk'): continue
        receipt = item.get('receipt') or {}
        key = (item['platform'], path.suffix, receipt.get('product', 'statusdesk'), receipt.get('channel', 'stable'))
        rank = (tuple(int(n) for n in version.split('.')) + (0,)*(4-len(version.split('.'))), item.get('run_id') or 0, path.stat().st_mtime_ns, relative)
        groups.setdefault(key, []).append((rank, relative))
    keep = {max(entries)[1] for entries in groups.values()}
    candidates = {relative for entries in groups.values() for _, relative in entries} - keep
    return plan(root, candidates, keep)


def plan_empty():
    return {'items': [], 'bytes': 0, 'token': ''}


def local_cleanup(token=None):
    with _lock:
        current = local_plan()
        if token is None: return current
        removed = {item['path'] for item in current['items']}
        markers = []
        for marker in library_root().glob('*/library.json'):
            # Keep the marker, even empty, so the build monitor doesn't redownload.
            safe_file(library_root(), marker.relative_to(library_root()).as_posix())
            entries = json.loads(marker.read_text(encoding='utf-8'))
            remaining = [e for e in entries if e['relative_path'] not in removed]
            if remaining != entries:
                markers.append((marker, remaining))
        result = remove(library_root(), current, token)
        for marker, remaining in markers:
            temporary = marker.with_suffix('.cleanup.tmp')
            temporary.write_text(json.dumps(remaining, ensure_ascii=False), encoding='utf-8')
            temporary.replace(marker)
        return result


def server_cleanup(token=None):
    config = json.loads((Path(settings.BASE_DIR)/'.local-publish.json').read_text(encoding='utf-8-sig'))
    host, user, port = config['host'], config['user'], config['port']
    if not re.fullmatch('[A-Za-z0-9.-]+', host) or not re.fullmatch('[a-z_][a-z0-9_-]*', user) or type(port) is not int or not 1 <= port <= 65535:
        raise ValueError('Invalid SSH settings')
    if token is not None and not re.fullmatch('[a-f0-9]{64}', token): raise ValueError('Invalid confirmation token')
    source = (Path(settings.BASE_DIR)/'updates/cleanup.py').read_text(encoding='utf-8')
    source += '\nprint(json.dumps(server_main('+repr(token)+'), ensure_ascii=True))\n'
    encoded = base64.b64encode(source.encode()).decode()
    command = 'sudo -n python3 -c '+shlex.quote('import base64;exec(base64.b64decode('+repr(encoded)+'))')
    args = ['C:/Program Files/PuTTY/plink.exe', *putty_connection(port, config['key_file'], config.get('host_key')), user+'@'+host, command]
    result = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=90)
    if result.returncode:
        raise ValueError('Не удалось выполнить очистку на сервере: '+result.stderr[-1800:])
    return json.loads(result.stdout)
