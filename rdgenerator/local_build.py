"""Local-only GitHub Actions transport; no callbacks or public local server."""
import base64
import io
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import uuid

import pyzipper
import requests
from django.conf import settings
from nacl.public import PublicKey, SealedBox


class LocalBuildError(Exception):
    pass


def github_session():
    git = os.environ.get('GIT_EXECUTABLE') or shutil.which('git')
    if not git:
        raise LocalBuildError('Git is not available. Start the constructor using start-local.ps1.')
    try:
        result = subprocess.run([git, 'credential', 'fill'],
            input=f'protocol=https\nhost=github.com\nusername={settings.GHUSER}\n\n',
            text=True, capture_output=True, timeout=20,
            env={**os.environ, 'GIT_TERMINAL_PROMPT': '0', 'GCM_INTERACTIVE': 'never'}, check=True)
        credentials = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
        token = credentials['password']
    except (subprocess.SubprocessError, KeyError, OSError) as exc:
        raise LocalBuildError('Sign in to GitHub using Git Credential Manager, then try again.') from exc
    session = requests.Session()
    session.headers.update({'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
                            'X-GitHub-Api-Version': '2026-03-10'})
    return session


def _base():
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', settings.GHUSER) or not re.fullmatch(r'[A-Za-z0-9_.-]+', settings.REPONAME):
        raise LocalBuildError('Set GHUSER and REPONAME for your GitHub fork.')
    return f'https://api.github.com/repos/{settings.GHUSER}/{settings.REPONAME}'


def _request(session, method, path, **kwargs):
    try:
        response = session.request(method, _base() + path, timeout=40, **kwargs)
        if method == "DELETE" and response.status_code == 404:
            return {}
        response.raise_for_status()
        return response.json() if response.content else {}
    except requests.RequestException as exc:
        code = getattr(getattr(exc, 'response', None), 'status_code', None)
        raise LocalBuildError(f'GitHub request failed ({code or "network error"}). Check sign-in and repository access.') from exc


def pack_configuration(inputs, images):
    password = secrets.token_urlsafe(48)
    buffer = io.BytesIO()
    with pyzipper.AESZipFile(buffer, 'w', compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as archive:
        archive.setpassword(password.encode())
        archive.writestr('secrets.json', json.dumps(inputs).encode())
        for name, data in images.items():
            if name not in ('icon.png', 'logo.png', 'privacy.png'):
                raise LocalBuildError('Unsupported build asset.')
            archive.writestr(name, data)
    if buffer.tell() > 8 * 1024 * 1024:
        raise LocalBuildError('Build configuration and images exceed 8 MB. Use smaller PNG images.')
    return buffer.getvalue(), password


def _record_path(build_id):
    if str(uuid.UUID(build_id)) != build_id:
        raise LocalBuildError('Invalid build ID.')
    directory = Path(settings.BASE_DIR) / '.local-builds'
    directory.mkdir(exist_ok=True)
    return directory / (build_id + '.json')


def _save(record):
    path = _record_path(record['id'])
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(record), encoding='utf-8')
    temporary.replace(path)


def dispatch_local(inputs, images, version, app_version=''):
    session = github_session()
    build_id = str(uuid.uuid4())
    branch = 'codex/build-input-' + build_id
    secret = 'STDESK_BUILD_' + build_id.replace('-', '').upper()
    payload, password = pack_configuration(inputs, images)
    workflow = 'generator-windows.yml'
    record = {'id': build_id, 'branch': branch, 'secret': secret, 'workflow': workflow,
              'status': 'queued', 'run_id': None, 'log_url': f'https://github.com/{settings.GHUSER}/{settings.REPONAME}/actions/workflows/{workflow}'}
    created_secret = created_branch = False
    try:
        public = _request(session, 'GET', '/actions/secrets/public-key')
        encrypted = SealedBox(PublicKey(base64.b64decode(public['key']))).encrypt(password.encode())
        _request(session, 'PUT', '/actions/secrets/' + secret,
                 json={'key_id': public['key_id'], 'encrypted_value': base64.b64encode(encrypted).decode()})
        created_secret = True
        ref = _request(session, 'GET', '/git/ref/heads/' + settings.GHBRANCH)
        _request(session, 'POST', '/git/refs', json={'ref': 'refs/heads/' + branch, 'sha': ref['object']['sha']})
        created_branch = True
        _request(session, 'PUT', '/contents/build-input.zip', json={'message': 'Encrypted input for local build ' + build_id,
            'branch': branch, 'content': base64.b64encode(payload).decode()})
        _save(record)
        details = _request(session, 'POST', f'/actions/workflows/{workflow}/dispatches', json={
            'ref': settings.GHBRANCH, 'inputs': {'version': version, 'app_version': app_version,
                'config_ref': branch, 'config_secret': secret, 'request_id': build_id}, 'return_run_details': True})
        record['run_id'] = details.get('workflow_run_id')
        record['log_url'] = details.get('html_url') or record['log_url']
        _save(record)
    except LocalBuildError:
        if created_branch:
            try:
                _request(session, 'DELETE', '/git/refs/heads/' + branch)
            except LocalBuildError:
                pass
        if created_secret:
            try:
                _request(session, 'DELETE', '/actions/secrets/' + secret)
            except LocalBuildError:
                pass
        raise
    return {'success': True, 'local_build': True, 'uuid': build_id, 'filename': inputs['filename'],
            'platform': 'windows', 'log_url': record['log_url']}


def local_status(build_id):
    try:
        record = json.loads(_record_path(build_id).read_text(encoding='utf-8'))
    except (ValueError, OSError) as exc:
        raise LocalBuildError('Build not found.') from exc
    session = github_session()
    if not record['run_id']:
        runs = _request(session, 'GET', '/actions/workflows/' + record['workflow'] + '/runs', params={'event': 'workflow_dispatch', 'per_page': 50})
        for run in runs['workflow_runs']:
            if build_id in run['display_title']:
                record['run_id'] = run['id']
                record['log_url'] = run['html_url']
                break
    if record['run_id']:
        run = _request(session, 'GET', '/actions/runs/' + str(record['run_id']))
        record['status'] = run['status']
        record['conclusion'] = run['conclusion']
        record['log_url'] = run['html_url']
        if run['status'] == 'completed' and not record.get('cleaned'):
            # Per-build keys are independent; cleanup never touches another build.
            try:
                _request(session, 'DELETE', '/actions/secrets/' + record['secret'])
                _request(session, 'DELETE', '/git/refs/heads/' + record['branch'])
                record['cleaned'] = True
            except LocalBuildError:
                record['cleanup_pending'] = True
    _save(record)
    return {key: record.get(key) for key in ('id', 'status', 'conclusion', 'log_url', 'cleaned', 'cleanup_pending')}


def collect_images(params):
    images = {}
    for prefix in ('icon', 'logo', 'privacy'):
        value = params.get(prefix + 'file') or params.get(prefix + 'base64')
        if not value:
            continue
        try:
            if hasattr(value, 'read'):
                value.seek(0)
                data = value.read()
            else:
                data = base64.b64decode(value.split(',', 1)[-1], validate=True)
            from PIL import Image
            image = Image.open(io.BytesIO(data))
            if image.format != 'PNG':
                raise ValueError('not PNG')
            image.verify()
        except Exception as exc:
            raise LocalBuildError(f'Invalid {prefix} PNG image.') from exc
        images[prefix + '.png'] = data
    return images


def recent_local_builds():
    directory = Path(settings.BASE_DIR) / '.local-builds'
    if not directory.exists():
        return []
    builds = []
    for path in sorted(directory.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True)[:10]:
        try:
            builds.append(json.loads(path.read_text(encoding='utf-8')))
        except (OSError, ValueError):
            continue
    return builds


def get_local_record(build_id):
    try:
        return json.loads(_record_path(build_id).read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise LocalBuildError('Build not found.') from exc
