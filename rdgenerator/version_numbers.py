"""Keep the selected product release shared by all platform builds."""
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


def _read():
    path = Path(settings.BASE_DIR) / '.local-version-counters.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def _release(values, base):
    parts(base, base + '.1')
    value = values.get(base, 1)
    # Existing counters become the current release, without resetting numbering.
    return {'latest': value, 'current': value} if isinstance(value, int) else value


def _write(values):
    path = Path(settings.BASE_DIR) / '.local-version-counters.json'
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(values, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def current_number(base):
    return _release(_read(), base)['current']


def create_next(base):
    with _locked():
        values = _read()
        number = _release(values, base)['latest'] + 1
        parts(base, f'{base}.{number}')
        values[base] = {'latest': number, 'current': number}
        _write(values)
    return f'{base}.{number}'


def reserve(base, requested=''):
    """Select a release for this build; retries and other platforms reuse it."""
    with _locked():
        values = _read()
        release = _release(values, base)
        number = parts(base, requested)[3] if requested and requested != base else release['current']
        display = f'{base}.{number}'
        parts(base, display)
        values[base] = {'latest': max(number, release['latest']), 'current': number}
        _write(values)
    return display
