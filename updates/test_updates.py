import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import io
import zipfile
import unittest

from nacl.exceptions import BadSignatureError
from nacl.signing import SigningKey

sys.path.insert(0, str(Path(__file__).parent))
from config import validate
from release import prepare, verify_envelope

spec = importlib.util.spec_from_file_location('update_adapter', Path(__file__).with_name('apply.py'))
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


class UpdateTests(unittest.TestCase):
    def config(self, key):
        return {'base_url': 'https://desk.status16.ru/client', 'public_key': key.verify_key.encode().hex(),
                'product': 'statusdesk', 'channel': 'test', 'revision': 2}

    def test_signed_bundle_rejects_tampered_metadata_and_wrong_key(self):
        key = SigningKey.generate()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'input'
            source.mkdir()
            receipt = {**self.config(key), 'schema': 1, 'platform': 'windows-x64', 'app_name': 'StatusDesk', 'version': '1.5.0'}
            (source / 'stdesk-update-build.json').write_text(json.dumps(receipt))
            binary = bytearray(256)
            binary[:2] = b'MZ'
            struct.pack_into('<I', binary, 0x3c, 128)
            binary[128:134] = b'PE\0\0\x64\x86'
            (source / 'StatusDesk.exe').write_bytes(binary)
            result = prepare(source, root / 'bundle', key.encode().hex(), 'StatusDesk', '1.5.0', '123', 'abc')
            data = (root / 'bundle/channels/statusdesk/test/windows-x64.json').read_bytes()
            self.assertEqual(verify_envelope(data, receipt['public_key']), result)
            from signed_bundle import pack, unpack
            package = pack(root / 'bundle', receipt['public_key'])
            unpack(package, receipt['public_key'], root / 'unpacked')
            # Extra files, including accidentally included private keys, never get uploaded.
            buffer = io.BytesIO(package)
            with zipfile.ZipFile(buffer, 'a') as archive:
                archive.writestr('signing-key.dpapi', b'private material')
            with self.assertRaisesRegex(ValueError, 'unexpected files'):
                unpack(buffer.getvalue(), receipt['public_key'], root / 'rejected')
            envelope = json.loads(data)
            envelope['payload'] = envelope['payload'].replace('"revision":2', '"revision":3')
            with self.assertRaises(BadSignatureError):
                verify_envelope(json.dumps(envelope), receipt['public_key'])
            with self.assertRaises(ValueError):
                prepare(source, root / 'wrong-key', SigningKey.generate().encode().hex(), 'StatusDesk', '1.5.0', '123', 'abc')

    def test_bad_configuration_and_unsupported_platform_fail(self):
        config = self.config(SigningKey.generate())
        for patch in ({'base_url': 'http://desk.status16.ru/client'}, {'base_url': 'https://desk.status16.ru/client?x=1'}, {'revision': True}, {'product': '../other'}, {'public_key': 'bad'}):
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                validate({**config, **patch})
        with self.assertRaises(ValueError):
            validate(config, platform='windows-x86')

    def test_adapter_is_opt_in_and_checks_all_anchors_before_writing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = Path(__file__).resolve().parents[2] / 'rustdesk'
            for file in ('src/updater.rs', 'src/common.rs'):
                target = root / file
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(subprocess.check_output(['git', '-c', f'safe.directory={source.as_posix()}', '-C', str(source), 'show', f'HEAD:{file}']))
            before = (root / 'src/updater.rs').read_bytes()
            adapter.apply(root, None)
            self.assertEqual(before, (root / 'src/updater.rs').read_bytes())
            adapter.apply(root, self.config(SigningKey.generate()))
            self.assertIn('return rdgen_update::check();', (root / 'src/updater.rs').read_text())
            self.assertNotIn('@KEY@', (root / 'src/rdgen_update.rs').read_text())
            after = (root / 'src/updater.rs').read_bytes()
            with self.assertRaises(ValueError):
                adapter.apply(root, self.config(SigningKey.generate()))
            self.assertEqual(after, (root / 'src/updater.rs').read_bytes())

    @unittest.skipUnless(sys.platform == 'win32', 'Windows DPAPI')
    def test_local_key_is_encrypted_and_reused_without_replacement(self):
        from local_key import initialize, load
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'key.dpapi'
            public = initialize(path)
            key = load(path)
            self.assertEqual(key.verify_key.encode().hex(), public)
            self.assertNotEqual(path.read_bytes(), key.encode())
            self.assertNotIn(key.encode().hex().encode(), path.read_bytes())
            before = path.read_bytes()
            self.assertEqual(initialize(path), public)
            self.assertEqual(path.read_bytes(), before)
            # A password-encrypted backup must restore the same signing identity.
            from unittest.mock import patch
            import local_release
            backup = Path(temporary) / 'backup.enc'
            with patch.object(local_release, 'KEY_FILE', path):
                with patch.object(sys, 'argv', ['local_release', 'backup', '--output', str(backup)]), patch('getpass.getpass', return_value='temporary-test-password-123'):
                    local_release.main()
                path.unlink()
                with patch.object(sys, 'argv', ['local_release', 'restore', '--backup', str(backup)]), patch('getpass.getpass', return_value='temporary-test-password-123'):
                    local_release.main()
            self.assertEqual(load(path).verify_key.encode().hex(), public)

    @unittest.skipIf(sys.platform == 'win32', 'Apache publication uses Linux file locking')
    def test_publication_is_monotonic_and_tampering_keeps_current_channel(self):
        from deploy import deploy
        key = SigningKey.generate()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'input'
            source.mkdir()
            receipt = {**self.config(key), 'schema': 1, 'platform': 'windows-x64', 'app_name': 'StatusDesk', 'version': '1.5.0'}
            (source / 'stdesk-update-build.json').write_text(json.dumps(receipt))
            binary = bytearray(256)
            binary[:2] = b'MZ'
            struct.pack_into('<I', binary, 0x3c, 128)
            binary[128:134] = b'PE\0\0\x64\x86'
            (source / 'client.exe').write_bytes(binary)
            prepare(source, root / 'bundle', key.encode().hex(), 'StatusDesk', '1.5.0', '123', 'abc')
            deploy(root / 'bundle', root / 'public', receipt['public_key'])
            channel = root / 'public/channels/statusdesk/test/windows-x64.json'
            previous = channel.read_bytes()
            with self.assertRaises(ValueError):
                deploy(root / 'bundle', root / 'public', receipt['public_key'])
            installer = root / 'bundle/releases/statusdesk/test/2/client-windows-x64.exe'
            installer.write_bytes(b'corrupted')
            with self.assertRaises(ValueError):
                deploy(root / 'bundle', root / 'public', receipt['public_key'])
            self.assertEqual(previous, channel.read_bytes())


if __name__ == '__main__':
    unittest.main()
