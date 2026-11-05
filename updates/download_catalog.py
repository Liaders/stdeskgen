"""Maintain the public downloads list independently of testing update channels."""
import json
import os
from pathlib import Path
import uuid


def update(root, platform, *, url, version):
    path = root / 'downloads.json'
    value = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'schema': 1, 'items': {}}
    if value.get('schema') != 1 or not isinstance(value.get('items'), dict):
        raise ValueError('Unsupported download catalog')
    value['items'][platform] = {'url': url, 'version': version}
    temporary = root / ('.downloads-' + uuid.uuid4().hex + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.chmod(0o644)
    os.replace(temporary, path)
