"""Local-only signing and explicit upload of a verified public update package."""
import argparse
import getpass
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import uuid

from local_key import initialize, load, store
from release import prepare
from signed_bundle import pack, unpack

ROOT = Path(__file__).resolve().parents[1]
KEY_FILE = ROOT / '.local-update-keys/signing-key.dpapi'


def github():
    sys.path.insert(0, str(ROOT))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rdgen.settings')
    from django.conf import settings
    from rdgenerator.local_build import github_session
    return github_session(), f'{settings.GHUSER}/{settings.REPONAME}', settings.GHBRANCH


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('init')
    backup = commands.add_parser('backup')
    backup.add_argument('--output', type=Path, required=True)
    restore = commands.add_parser('restore')
    restore.add_argument('--backup', type=Path, required=True)
    build = commands.add_parser('prepare')
    build.add_argument('--run-id', type=int, required=True)
    build.add_argument('--output', type=Path, required=True)
    publish = commands.add_parser('publish')
    publish.add_argument('--bundle', type=Path, required=True)
    publish.add_argument('--deploy', action='store_true')
    args = parser.parse_args()
    if args.command == 'restore':
        from nacl import pwhash, secret
        from nacl.signing import SigningKey
        if KEY_FILE.exists():
            raise ValueError('A signing key already exists; refusing replacement')
        data = json.loads(args.backup.read_text(encoding='utf-8'))
        if data.get('schema') != 1 or data.get('kdf') != 'argon2id-moderate':
            raise ValueError('Unknown backup format')
        password = getpass.getpass('Backup password: ')
        derived = pwhash.argon2id.kdf(secret.SecretBox.KEY_SIZE, password.encode(), bytes.fromhex(data['salt']),
            opslimit=pwhash.argon2id.OPSLIMIT_MODERATE, memlimit=pwhash.argon2id.MEMLIMIT_MODERATE)
        key = SigningKey(secret.SecretBox(derived).decrypt(bytes.fromhex(data['ciphertext'])))
        if key.verify_key.encode().hex() != data['public_key']:
            raise ValueError('Backup public key mismatch')
        public = store(KEY_FILE, key)
        (KEY_FILE.parent / 'public-key.hex').write_text(public + '\n', encoding='utf-8')
        print('Local signing key restored:', public)
        return
    if args.command == 'init':
        public = initialize(KEY_FILE)
        (KEY_FILE.parent / 'public-key.hex').write_text(public + '\n', encoding='utf-8')
        config = {'base_url': 'https://desk.status16.ru/client', 'public_key': public,
                  'product': 'statusdesk', 'channel': 'test', 'revision': 1}
        path = ROOT / 'updates/statusdesk-test.example.json'
        if not path.exists():
            path.write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')
        print('Public signing key:', public)
        print('Private key protected with Windows DPAPI; no network requests made.')
        return
    if args.command == 'backup':
        from nacl import pwhash, secret, utils
        password = getpass.getpass('Backup password (never sent anywhere): ')
        if len(password) < 12 or password != getpass.getpass('Repeat backup password: '):
            raise ValueError('Use at least 12 characters and matching passwords')
        salt = utils.random(pwhash.argon2id.SALTBYTES)
        derived = pwhash.argon2id.kdf(secret.SecretBox.KEY_SIZE, password.encode(), salt,
            opslimit=pwhash.argon2id.OPSLIMIT_MODERATE, memlimit=pwhash.argon2id.MEMLIMIT_MODERATE)
        key = load(KEY_FILE)
        data = {'schema': 1, 'kdf': 'argon2id-moderate', 'salt': salt.hex(),
                'ciphertext': bytes(secret.SecretBox(derived).encrypt(key.encode())).hex(),
                'public_key': key.verify_key.encode().hex()}
        with args.output.open('x', encoding='utf-8') as stream:
            json.dump(data, stream)
        print('Encrypted backup saved. Keep it and its password outside this repository.')
        return
    if args.command == 'prepare':
        if args.output.exists():
            raise ValueError('Output directory already exists')
        session, repository, _ = github()
        from fetch_build import fetch
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / 'input'
            commit = fetch(args.run_id, source, session=session, repository=repository)
            receipt = json.loads((source / 'stdesk-update-build.json').read_text(encoding='utf-8'))
            key = load(KEY_FILE)
            manifest = prepare(source, args.output, key.encode().hex(), receipt['app_name'], receipt['version'], str(args.run_id), commit)
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        print('Signed locally. Nothing uploaded; inspect this bundle before publishing.')
        return
    # Publication needs only the public key. Never unlock or read the private key here.
    public = (KEY_FILE.parent / 'public-key.hex').read_text(encoding='utf-8').strip()
    data = pack(args.bundle, public)
    with tempfile.TemporaryDirectory() as temporary:
        manifest = unpack(data, public, Path(temporary) / 'verified')
    session, repository, branch = github()
    base = 'https://api.github.com/repos/' + repository
    # Only a PUBLIC key is transferred to the verification workflow.
    response = session.get(base + '/actions/variables/STDESK_UPDATE_PUBLIC_KEY', timeout=30)
    if response.status_code == 404:
        response = session.post(base + '/actions/variables', json={'name': 'STDESK_UPDATE_PUBLIC_KEY', 'value': public}, timeout=30)
        response.raise_for_status()
    else:
        response.raise_for_status()
        if response.json()['value'] != public:
            raise ValueError('GitHub public verification key differs; refusing replacement')
    tag = f"signed-{manifest['product']}-{manifest['channel']}-{manifest['revision']}-{uuid.uuid4().hex[:8]}"
    response = session.post(base + '/releases', json={'tag_name': tag, 'target_commitish': branch,
        'name': tag, 'draft': True, 'body': 'Locally signed StatusDesk update package; contains no private signing key.'}, timeout=30)
    response.raise_for_status()
    release = response.json()
    response = session.post(release['upload_url'].split('{')[0], params={'name': 'signed-client-update.zip'},
        headers={'Content-Type': 'application/zip'}, data=data, timeout=600)
    response.raise_for_status()
    asset = response.json()
    response = session.post(base + '/actions/workflows/publish-client-update.yml/dispatches', json={
        'ref': branch, 'inputs': {'release_id': str(release['id']), 'asset_id': str(asset['id']),
                                'package_sha256': hashlib.sha256(data).hexdigest(), 'deploy': args.deploy}}, timeout=30)
    response.raise_for_status()
    print('Signed package uploaded as a draft release:', release['html_url'])
    print('Verification/publication dispatched; private signing key stayed local.')


if __name__ == '__main__':
    main()
