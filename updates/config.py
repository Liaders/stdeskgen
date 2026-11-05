"""Validated, opt-in configuration for the StatusDesk update channel."""
import re
from urllib.parse import urlsplit


def validate(raw, version='1.5.0', platform='windows'):
    import json
    if raw in (None, ''):
        return None
    value = json.loads(raw) if isinstance(raw, str) else raw
    fields = {'base_url', 'public_key', 'product', 'channel', 'revision'}
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError('Update configuration requires base_url, public_key, product, channel and revision')
    if version != '1.5.0' or platform != 'windows':
        raise ValueError('Signed updates currently support RustDesk 1.5.0 / Windows x64 only')
    if any(not isinstance(value[field], str) for field in fields - {'revision'}):
        raise ValueError('Update configuration text fields must be strings')
    url = urlsplit(value['base_url'])
    if (url.scheme != 'https' or not url.hostname or url.username or url.password
            or url.query or url.fragment or url.port not in (None, 443)
            or not re.fullmatch(r'https://[A-Za-z0-9.-]+(?:/[A-Za-z0-9_-]+)*', value['base_url'])):
        raise ValueError('Update base_url must be an HTTPS URL without trailing slash, credentials or query')
    if not re.fullmatch('[0-9a-f]{64}', value['public_key']):
        raise ValueError('Update public_key must be the 32-byte Ed25519 public key in lowercase hex')
    for field in ('product', 'channel'):
        if not isinstance(value[field], str) or not re.fullmatch('[a-z][a-z0-9-]{0,47}', value[field]):
            raise ValueError(f'Update {field} must contain lowercase letters, digits or hyphens')
    if type(value['revision']) is not int or not 1 <= value['revision'] <= 2147483647:
        raise ValueError('Update revision must be an integer between 1 and 2147483647')
    return value
