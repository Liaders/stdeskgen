"""Loopback-only desktop endpoints. Publication is always an explicit CSRF-protected POST."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import threading
import uuid

from django.conf import settings
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from .build_downloads import library, library_root, find_installer, detect_platform
from .build_monitor import start
from .local_build import recent_local_builds, get_local_record, _save

_task = {'state': 'idle', 'message': ''}
_task_lock = threading.Lock()


def local(request):
    return settings.LOCAL_GITHUB_BUILD and request.META.get('REMOTE_ADDR') in ('127.0.0.1', '::1')


def status(request):
    if not local(request): return HttpResponseForbidden('Local only')
    start()
    return JsonResponse({'desktop_api': 1, 'download_directory': str(library_root()), 'publication': dict(_task)})


def builds(request):
    if not local(request): return HttpResponseForbidden('Local only')
    start()
    records = [{k: r.get(k) for k in ('id', 'filename', 'platform', 'run_id', 'status', 'conclusion', 'log_url', 'download_status', 'download_error', 'download_directory')} for r in recent_local_builds()]
    return JsonResponse({'builds': records})


def installers(request):
    if not local(request): return HttpResponseForbidden('Local only')
    return JsonResponse({'items': library(), 'directory': str(library_root())})


def publication_page(request):
    if not local(request): return HttpResponseForbidden('Local only')
    return render(request, 'publication.html')


@require_POST
@csrf_protect
def default_config(request):
    if not local(request): return HttpResponseForbidden('Local only')
    from .default_config import save
    try:
        if len(request.body) > 8 * 1024**2: raise ValueError('Configuration exceeds 8 MB')
        save(json.loads(request.body))
        return JsonResponse({'ok': True})
    except (OSError, ValueError) as exc:
        return JsonResponse({'error': str(exc)}, status=400)


def next_version(request):
    if not local(request): return HttpResponseForbidden('Local only')
    from .version_numbers import next_number
    from customization.versioning import SUPPORTED_BASES
    base = request.GET.get('base', '1.5.0')
    if base not in SUPPORTED_BASES: return JsonResponse({'error': 'Unsupported base'}, status=400)
    return JsonResponse({'version': base + '.' + str(next_number(base))})


@require_POST
@csrf_protect
def open_folder(request):
    if not local(request): return HttpResponseForbidden('Local only')
    library_root().mkdir(exist_ok=True)
    os.startfile(library_root())
    return JsonResponse({'ok': True})


@require_POST
@csrf_protect
def retry(request):
    if not local(request): return HttpResponseForbidden('Local only')
    data = json.loads(request.body)
    record = get_local_record(data['id'])
    record.pop('download_status', None)
    record.pop('download_error', None)
    _save(record)
    start()
    return JsonResponse({'ok': True})


@require_POST
@csrf_protect
def import_installer(request):
    if not local(request): return HttpResponseForbidden('Local only')
    upload = request.FILES.get('file')
    if not upload or not 0 < upload.size <= 512 * 1024**2:
        return JsonResponse({'error': 'Выберите установщик размером до 512 МБ.'}, status=400)
    folder = library_root() / ('import-' + uuid.uuid4().hex)
    folder.mkdir(parents=True)
    name = Path(upload.name).name
    path = folder / name
    try:
        with path.open('wb') as output:
            for chunk in upload.chunks(): output.write(chunk)
        platform = detect_platform(path, request.POST.get('platform', ''))
        relative = path.relative_to(library_root()).as_posix()
        with path.open('rb') as stream: digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        entry = {'id': hashlib.sha256(relative.encode()).hexdigest(), 'relative_path': relative, 'filename': name,
                 'platform': platform, 'size': upload.size, 'sha256': digest, 'version': request.POST.get('version', '1.5.0'), 'receipt': None, 'build_id': None}
        (folder / 'library.json').write_text(json.dumps([entry], ensure_ascii=False), encoding='utf-8')
        return JsonResponse({'ok': True, 'id': entry['id']})
    except (ValueError, OSError) as exc:
        return JsonResponse({'error': str(exc)}, status=400)


@require_POST
@csrf_protect
def publish(request):
    if not local(request): return HttpResponseForbidden('Local only')
    try:
        data = json.loads(request.body)
        entry, path = find_installer(data['id'])
        auto = data.get('auto_update') is True
        if auto and not entry.get('receipt'):
            raise ValueError('В этой сборке нет поддержки канала обновлений. Создайте клиент с включённым каналом в конструкторе.')
        if path.suffix not in ('.exe', '.deb', '.AppImage', '.dmg'):
            raise ValueError('Выберите EXE, DEB, AppImage или DMG.')
        version = data.get('version') or entry['version']
        with _task_lock:
            if _task['state'] == 'running': return JsonResponse({'error': 'Публикация уже выполняется.'}, status=409)
            _task.update(state='running', message='Передаём файл на сервер…')
        def run():
            command = [str(Path(settings.BASE_DIR) / '.venv/Scripts/python.exe'),
                       str(Path(settings.BASE_DIR) / 'updates/publish_from_windows.py'),
                       '--file', str(path), '--platform', entry['platform'], '--version', version]
            if auto: command += ['--receipt', str(path.parent / 'stdesk-update-build.json')]
            try:
                result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=1200,
                                        env={**os.environ, 'PYTHONUTF8': '1'})
                with _task_lock:
                    _task.update(state='success' if result.returncode == 0 else 'error', message=(result.stdout + '\n' + result.stderr)[-12000:])
            except Exception as exc:
                with _task_lock: _task.update(state='error', message=str(exc))
        threading.Thread(target=run, name='publish-installer', daemon=True).start()
        return JsonResponse({'ok': True})
    except (ValueError, KeyError) as exc:
        return JsonResponse({'error': str(exc)}, status=400)
