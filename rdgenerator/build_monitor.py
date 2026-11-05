"""One process-local worker for status refresh and automatic downloads."""
import threading
import time

_lock = threading.Lock()
_started = False


def start():
    global _started
    with _lock:
        if _started: return
        _started = True
    threading.Thread(target=run, name='local-build-monitor', daemon=True).start()


def run():
    from .local_build import recent_local_builds, local_status
    import logging
    while True:
        for record in recent_local_builds(limit=None):
            if record.get('download_status') == 'error': continue
            if record.get('conclusion') == 'dispatch_failed': continue
            if record.get('status') == 'completed' and record.get('download_status') == 'completed' and record.get('cleaned'): continue
            if record.get('status') == 'completed' and record.get('conclusion') not in (None, 'success') and record.get('cleaned'): continue
            try:
                local_status(record['id'])
            except Exception as exc:
                logging.getLogger(__name__).warning('Build monitor: %s', exc)
        for record in recent_local_builds(limit=None):
            if record.get('status') == 'completed' and record.get('conclusion') == 'success' and record.get('download_status') not in ('completed','error'):
                try:
                    local_status(record['id'], download=True)
                except Exception as exc:
                    logging.getLogger(__name__).warning('Artifact download: %s', exc)
        time.sleep(20)
