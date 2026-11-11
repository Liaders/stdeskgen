"""Use the runner's verified Ubuntu archive public keys for ARM64 AppImages."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import tempfile

FINGERPRINTS = (
    '790BC7277767219C42C86F933B4FE6ACC0B21F32',
    'F6ECB3762474EDA9D21B7022871920D1991BC93C',
)
KEY_URL = r"(?m)^([ \t]+key_url:[ \t]*)['\"]?http://keyserver\.ubuntu\.com/pks/lookup\?op=get&search=0x3b4fe6acc0b21f32['\"]?[ \t]*$"


def prepare(recipe, output, keyring=Path('/usr/share/keyrings/ubuntu-archive-keyring.gpg')):
    text = recipe.read_text(encoding='utf-8')
    if len(re.findall(KEY_URL, text)) != 4:
        raise ValueError('Unexpected ARM64 AppImage Ubuntu key URLs; review recipe')
    if not keyring.is_file(): raise ValueError('Ubuntu archive keyring is missing')
    with tempfile.TemporaryDirectory() as home:
        gpg = ['gpg', '--batch', '--homedir', home, '--no-default-keyring', '--keyring', str(keyring)]
        result = subprocess.run(gpg+['--with-colons','--fingerprint','--list-keys',*FINGERPRINTS],
            check=True, capture_output=True, text=True, timeout=20)
        found = {line.split(':')[9] for line in result.stdout.splitlines() if line.startswith('fpr:')}
        if not set(FINGERPRINTS).issubset(found):
            raise ValueError('Ubuntu archive signing-key fingerprint mismatch')
        exported = subprocess.run(gpg+['--armor','--export',*FINGERPRINTS],
            check=True, capture_output=True, timeout=20).stdout
    if not exported.startswith(b'-----BEGIN PGP PUBLIC KEY BLOCK-----'):
        raise ValueError('Ubuntu public-key export is empty or invalid')
    local_url = output.resolve().as_uri()
    updated = re.sub(KEY_URL, lambda match: match[1]+json.dumps(local_url), text)
    updated, count = re.subn(r'(?m)^([ \t]+allow_unauthenticated:)[ \t]+true[ \t]*$', r'\1 false', updated)
    if count != 1: raise ValueError('Unexpected ARM64 AppImage APT trust configuration')
    updated = updated.replace('http://ports.ubuntu.com/ubuntu-ports/', 'https://ports.ubuntu.com/ubuntu-ports/')
    output.write_bytes(exported)
    recipe.write_text(updated, encoding='utf-8')
    return local_url


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recipe', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.recipe, args.output)
    print('AppImage ARM64 uses verified local Ubuntu archive public keys')
