"""The operator's default profile is local data, never a repository asset."""
import json
from pathlib import Path
import uuid

from django.conf import settings


def path():
    return Path(settings.BASE_DIR) / 'default-config.json'


def save(config):
    if not isinstance(config, dict): raise ValueError('Expected a configuration object')
    config = {key: value for key, value in config.items() if key != 'csrfmiddlewaretoken'}
    temporary = path().with_name('.default-config-' + uuid.uuid4().hex + '.tmp')
    temporary.write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.chmod(0o600)
    temporary.replace(path())


def load():
    if not path().exists():
        save({'version': '1.5.0', 'platform': 'windows', 'exename': 'StatusDesk', 'appname': 'StatusDesk',
              'direction': 'both', 'installation': 'installationY', 'settings': 'settingsY', 'build_number': '',
              'ui_profile': {'schema_version': 1, 'accent': '#EF7F1A', 'button': '#EF7F1A', 'navigation': 'text',
                             'colleagues': True, 'device_names': True, 'resizable_panels': True,
                             'group_width': 260, 'address_book_width': 260}})
    config = json.loads(path().read_text(encoding='utf-8-sig'))
    if not isinstance(config, dict): raise ValueError('default-config.json must contain an object')
    config.pop('csrfmiddlewaretoken', None)
    return config
