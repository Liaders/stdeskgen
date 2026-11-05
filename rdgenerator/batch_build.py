"""Dispatch one release for every supported desktop platform."""
from .version_numbers import current_number


def build_all(params, full_url):
    from .views import generate_custom_client
    release = params.get('build_number') or current_number(params['version'])
    results = []
    for platform in ('windows', 'windows-x86', 'linux', 'macos'):
        config = {**params, 'platform': platform, 'build_number': release}
        if platform == 'windows-x86': config['ui_profile'] = ''
        if platform in ('linux','macos'): config['updates_config'] = ''
        try:
            result = generate_custom_client(config, full_url)
        except Exception:
            result = {'success': False, 'error': 'Не удалось отправить запрос сборки. Проверьте последние сборки перед повтором.'}
        results.append({**result, 'platform': platform})
    return results
