"""Select the newest publishable distribution for each download-page platform."""
from pathlib import Path
import re

PLATFORMS = ('windows-x64','windows-x86','linux-x64','linux-arm64','macos-x64','macos-arm64')


def latest_installers(items):
    selected = {}
    for item in items:
        if item.get('platform') not in PLATFORMS: continue
        extension = Path(item['filename']).suffix
        if extension not in ('.exe','.deb','.AppImage','.dmg'): continue
        match = re.fullmatch(r'(\d+)\.(\d+)\.(\d+)(?:\.(\d+))?', item.get('version',''))
        if not match: continue
        receipt = item.get('receipt')
        # Test channels must never become a public release through this shortcut.
        if receipt and (receipt.get('product') != 'statusdesk' or receipt.get('channel') != 'stable'): continue
        version = tuple(int(n or 0) for n in match.groups())
        key = (version, item.get('run_id') or 0, extension == '.deb', item['filename'], item['id'])
        previous = selected.get(item['platform'])
        if previous is None or key > previous[0]: selected[item['platform']] = (key,item)
    return [selected[p][1] for p in PLATFORMS if p in selected]
