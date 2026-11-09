"""Maintain the public downloads list independently of testing update channels."""
import json
import os
from pathlib import Path
import uuid
import zipfile
from urllib.parse import urlsplit, unquote


def update(root, platform, *, url, version):
    path = root / 'downloads.json'
    value = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'schema': 1, 'items': {}}
    if value.get('schema') != 1 or not isinstance(value.get('items'), dict):
        raise ValueError('Unsupported download catalog')
    item = {'url': url, 'version': version}
    if platform in ('windows-x64', 'windows-x86'):
        parsed = urlsplit(url)
        if not parsed.scheme and not parsed.netloc and parsed.path.startswith('/client/'):
            source = root / unquote(parsed.path.removeprefix('/client/'))
            if not source.resolve().is_relative_to(root.resolve()):
                raise ValueError('Unsafe Windows installer URL')
            if source.suffix.lower() == '.exe' and source.is_file():
                target = source.with_suffix('.zip')
                staging = target.with_name('.zip-' + uuid.uuid4().hex + '.tmp')
                try:
                    with zipfile.ZipFile(staging, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
                        archive.write(source, 'StatusDesk.exe' if platform == 'windows-x64' else 'StatusDesk-x32.exe')
                    staging.chmod(0o644)
                    os.replace(staging, target)
                finally:
                    staging.unlink(missing_ok=True)
                item['zip_url'] = parsed.path[:-4] + '.zip'
    value['items'][platform] = item
    temporary = root / ('.downloads-' + uuid.uuid4().hex + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.chmod(0o644)
    os.replace(temporary, path)


if __name__ == '__main__':
    import argparse
    import fcntl
    parser = argparse.ArgumentParser(description='Create ZIP alternatives for published Windows EXE installers.')
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    with (args.root / '.publish.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        catalog = json.loads((args.root / 'downloads.json').read_text(encoding='utf-8'))
        if catalog.get('schema') != 1 or not isinstance(catalog.get('items'), dict):
            raise ValueError('Unsupported download catalog')
        for platform in ('windows-x64', 'windows-x86'):
            item = catalog['items'].get(platform)
            if item:
                update(args.root, platform, url=item['url'], version=item['version'])
                print('ZIP alternative prepared for', platform)
