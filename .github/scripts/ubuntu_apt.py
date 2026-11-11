"""Select reachable Ubuntu mirrors on disposable GitHub-hosted build runners."""
import platform
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlsplit

FALLBACKS = [
    'https://azure.archive.ubuntu.com/ubuntu/',
    'https://archive.ubuntu.com/ubuntu/',
    'https://security.ubuntu.com/ubuntu/',
    'https://mirrors.edge.kernel.org/ubuntu/',
]


def reachable(base, codename):
    for suite in (codename, codename+'-updates', codename+'-backports', codename+'-security'):
        result = subprocess.run(['curl', '--fail', '--silent', '--show-error',
            '--connect-timeout', '3', '--max-time', '6', '--output', '/dev/null',
            base+'dists/'+suite+'/InRelease'], capture_output=True, text=True)
        if result.returncode:
            print('Skipping mirror '+base+': '+result.stderr.strip()[:200], flush=True)
            return False
    return True


def configure(apt_root, codename, probe=reachable):
    mirrors = apt_root/'apt-mirrors.txt'
    existing = mirrors.read_text().splitlines() if mirrors.exists() else []
    candidates = []
    for line in existing+FALLBACKS:
        if not line.strip() or line.lstrip().startswith('#'): continue
        uri = line.split()[0]
        parts = urlsplit(uri)
        if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
            continue
        uri = ('https://'+uri.split('://', 1)[1]).rstrip('/')+'/'
        if uri not in candidates: candidates.append(uri)
    healthy = [uri for uri in candidates if probe(uri, codename)]
    if not healthy:
        raise RuntimeError('No reachable Ubuntu package mirror; check runner DNS/network')
    target = 'mirror+file:'+mirrors.as_posix()
    sources = apt_root/'sources.list.d/ubuntu.sources'
    legacy = apt_root/'sources.list'
    if sources.exists():
        original = sources.read_text()
        updated, count = re.subn(r'^URIs:.*$', 'URIs: '+target, original, flags=re.M)
        if not count: raise RuntimeError('Ubuntu sources have no URIs field')
        updates = {sources: updated}
    elif legacy.exists():
        original = legacy.read_text()
        updated, count = re.subn(
            r'(?m)^(deb(?:-src)?\s+(?:\[[^\]]+\]\s+)?)(?:https?://[^\s]*ubuntu\.com/ubuntu/?|mirror\+file:\S+)',
            lambda match: match[1]+target, original)
        if not count: raise RuntimeError('Ubuntu sources have no recognized mirror URI')
        updates = {legacy: updated}
    else:
        raise RuntimeError('Ubuntu APT sources were not found')
    updates[mirrors] = ''.join(uri+'\tpriority:'+str(i)+'\n' for i,uri in enumerate(healthy, 1))
    updates[apt_root/'apt.conf.d/80rdgen-network'] = (
        'Acquire::Retries "1";\nAcquire::http::Timeout "15";\n'
        'Acquire::https::Timeout "15";\nAPT::Update::Error-Mode "any";\n')
    for path, text in updates.items(): path.write_text(text)
    print('Ubuntu '+codename+' mirrors: '+', '.join(healthy), flush=True)
    return healthy


if __name__ == '__main__':
    try:
        codename = platform.freedesktop_os_release()['VERSION_CODENAME']
        configure(Path('/etc/apt'), codename)
    except (OSError, KeyError, RuntimeError) as error:
        print('::error::'+str(error), file=sys.stderr)
        sys.exit(1)
