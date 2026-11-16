"""Compare analyzer errors before/after desktop adapters using a generated bridge."""
import argparse
from collections import Counter
import os
from pathlib import Path
import subprocess


def errors(root):
    result = subprocess.run(['dart', 'analyze', '--format=machine', 'lib'],
        cwd=root/'flutter', text=True, encoding='utf-8', errors='replace',
        capture_output=True, timeout=300)
    if result.returncode not in (0, 1, 2, 3):
        raise RuntimeError('Dart analyzer failed: '+result.stderr[-2000:])
    diagnostics = Counter()
    for line in (result.stdout+'\n'+result.stderr).splitlines():
        fields = line.split('|', 7)
        if len(fields) == 8 and fields[0] == 'ERROR':
            name = Path(fields[3]).relative_to(root.resolve()).as_posix()
            diagnostics[(name, fields[2], fields[7])] += 1
    if not diagnostics and 'No issues found' not in result.stdout and result.returncode != 0:
        raise RuntimeError('Analyzer returned no readable diagnostics: '+result.stdout[-2000:])
    return diagnostics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    root = args.source.resolve()
    subprocess.run(['flutter', 'pub', 'get'], cwd=root/'flutter', check=True, timeout=600)
    before = errors(root)
    from desktop_chrome import apply_flutter
    from session_titles import apply as apply_titles
    from session_work_groups import apply as apply_groups
    from desktop_ui import apply as apply_desktop
    from apply_profile import apply as apply_profile
    from apply_version import apply as apply_version
    profile = {'schema_version':1, 'navigation':'text', 'organizations':True,
        'colleagues':True, 'device_names':True, 'resizable_panels':True, 'slim_ui':True}
    apply_flutter(root)
    apply_titles(root)
    apply_groups(root)
    apply_desktop(root, profile)
    apply_profile(root, '1.5.1', profile)
    apply_version(root, '1.5.1', '1.5.1.999')
    after = errors(root)
    introduced = after - before
    print(f'Original analyzer errors: {sum(before.values())}; patched: {sum(after.values())}; introduced: {sum(introduced.values())}')
    for (name, code, message), count in introduced.items():
        print(f'{name}: {code}: {message} ({count})')
    if introduced:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
