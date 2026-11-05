"""Apply a four-part product version without placing invalid SemVer in Cargo.toml."""
import argparse
import json
import os
from pathlib import Path
import re

from versioning import parts, revision


def apply(root, base, display):
    values = parts(base, display)
    edits = {}
    path = root / 'src/ui_interface.rs'
    source = path.read_text(encoding='utf-8')
    old = 'pub fn get_version() -> String {\n    crate::VERSION.to_owned()\n}'
    if source.count(old) != 1: raise ValueError('Incompatible version presentation function')
    edits[path] = source.replace(old, 'pub fn get_version() -> String {\n    ' + json.dumps(display) + '.to_owned()\n}', 1)
    path = root / 'build.py'
    source = path.read_text(encoding='utf-8')
    start = source.index('def get_version():')
    end = source.index('\ndef ', start + 1)
    edits[path] = source[:start] + 'def get_version():\n    return ' + repr(display) + '\n\n' + source[end:]
    path = root / 'flutter/pubspec.yaml'
    source = path.read_text(encoding='utf-8')
    source, count = re.subn(r'^version:.*$', f'version: {base}+{values[3]}', source, count=1, flags=re.M)
    if count != 1: raise ValueError('Missing Flutter version')
    edits[path] = source
    path = root / 'flutter/windows/runner/Runner.rc'
    source = path.read_text(encoding='utf-8')
    source = re.sub(r'^#define VERSION_AS_NUMBER .*$', '#define VERSION_AS_NUMBER ' + ','.join(map(str, values)), source, flags=re.M)
    source = re.sub(r'^#define VERSION_AS_STRING .*$', '#define VERSION_AS_STRING ' + json.dumps(display), source, flags=re.M)
    edits[path] = source
    packed = revision(base, display)
    path = root / 'src/platform/windows.rs'
    source = path.read_text(encoding='utf-8')
    source = source.replace('let version = crate::VERSION.replace("-", ".");', 'let version = crate::ui_interface::get_version();')
    edits[path] = source
    for relative in ('build.rs', 'libs/portable/build.rs'):
        path = root / relative
        source = path.read_text(encoding='utf-8')
        anchor = 'res.set_icon('
        if source.count(anchor) != 1: raise ValueError('Incompatible Windows version resources: ' + relative)
        source = source.replace(anchor,
            f'res.set_version_info(winres::VersionInfo::FILEVERSION, {packed});\n'
            f'        res.set_version_info(winres::VersionInfo::PRODUCTVERSION, {packed});\n'
            f'        res.set("FileVersion", {json.dumps(display)});\n'
            f'        res.set("ProductVersion", {json.dumps(display)});\n'
            '        ' + anchor, 1)
        edits[path] = source
    for path, value in edits.items(): path.write_text(value, encoding='utf-8')
    metadata = {'base_version': base, 'version': display, 'build_number': values[3]}
    (root / 'stdesk-version.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=Path('.'))
    parser.add_argument('--base-version', required=True)
    parser.add_argument('--display-version', required=True)
    args = parser.parse_args()
    apply(args.source, args.base_version, args.display_version)
    if os.environ.get('GITHUB_ENV'):
        with open(os.environ['GITHUB_ENV'], 'a', encoding='utf-8') as output:
            output.write('stdesk_display_version=' + args.display_version + '\n')
