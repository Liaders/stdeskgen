"""Reserve unique client build numbers across local constructor processes."""
from contextlib import contextmanager
import json
import os
from pathlib import Path

from django.conf import settings
from customization.versioning import parts


@contextmanager
def _locked():
    path = Path(settings.BASE_DIR) / '.local-version-counters.lock'
    with path.open('a+b') as stream:
        if stream.tell() == 0: stream.write(b'0'); stream.flush()
        stream.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(stream, fcntl.LOCK_EX)
        try: yield
        finally:
            stream.seek(0)
            if os.name == 'nt': msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else: fcntl.flock(stream, fcntl.LOCK_UN)


def next_number(base):
    path = Path(settings.BASE_DIR) / '.local-version-counters.json'
    values = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    return values.get(base, 0) + 1


def reserve(base, requested=''):
    path = Path(settings.BASE_DIR) / '.local-version-counters.json'
    with _locked():
        values = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
        number = parts(base, requested)[3] if requested and requested != base else values.get(base, 0) + 1
        display = f'{base}.{number}'
        parts(base, display)
        if number <= values.get(base, 0):
            raise ValueError('This build number is already reserved; leave it empty for automatic numbering')
        values[base] = number
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(values, indent=2) + '\n', encoding='utf-8')
        temporary.replace(path)
    return display
