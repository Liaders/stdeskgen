import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))
from config import validate
from release import prepare, load_manifest

spec = importlib.util.spec_from_file_location('update_adapter', Path(__file__).with_name('apply.py'))
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


class UpdateTests(unittest.TestCase):
    config = {'base_url': 'https://desk.status16.ru/client',
              'product': 'statusdesk', 'channel': 'test', 'revision': 2}

    def source(self, root):
        source = root / 'input'
        source.mkdir()
        receipt = {**self.config, 'schema': 2, 'platform': 'windows-x64', 'app_name': 'StatusDesk', 'version': '1.5.0'}
        (source / 'stdesk-update-build.json').write_text(json.dumps(receipt))
        binary = bytearray(256)
        binary[:2] = b'MZ'
        struct.pack_into('<I', binary, 0x3c, 128)
        binary[128:134] = b'PE\0\0\x64\x86'
        (source / 'client.exe').write_bytes(binary)
        return source

    def test_package_needs_no_keys_and_records_binary_integrity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = prepare(self.source(root), root / 'bundle', 'StatusDesk', '1.5.0', '123', 'abc')
            data = (root / 'bundle/channels/statusdesk/test/windows-x64.json').read_bytes()
            self.assertEqual(load_manifest(data), result)
            self.assertEqual(result['size'], 256)
            self.assertEqual(len(result['sha256']), 64)
            self.assertNotIn('signature', result)

    def test_catalog_preserves_other_platforms(self):
        from download_catalog import update
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            update(root, 'windows-x86', url='/client/downloads/x86.exe', version='1.5.0')
            update(root, 'macos-arm64', url='/client/downloads/mac.dmg', version='1.5.0')
            catalog = json.loads((root / 'downloads.json').read_text())
            self.assertEqual(set(catalog['items']), {'windows-x86', 'macos-arm64'})

    def test_bad_configuration_and_unsupported_platform_fail(self):
        self.assertEqual(validate(self.config, platform='windows-x86'), self.config)
        for patch in ({'base_url': 'http://desk.status16.ru/client'}, {'revision': True}, {'product': '../other'}, {'public_key': 'obsolete'}):
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                validate({**self.config, **patch})
        with self.assertRaises(ValueError):
            validate(self.config, platform='linux')

    def test_adapter_is_opt_in_and_rejects_reapplying_without_partial_writes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = Path(__file__).resolve().parents[2] / 'rustdesk'
            for file in ('src/updater.rs', 'src/common.rs', 'Cargo.toml'):
                target = root / file
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(subprocess.check_output(['git', '-c', f'safe.directory={source.as_posix()}', '-C', str(source), 'show', os.environ.get('RUSTDESK_TEST_REF', 'HEAD') + ':' + file]))
            before = (root / 'src/updater.rs').read_bytes()
            adapter.apply(root, None)
            self.assertEqual(before, (root / 'src/updater.rs').read_bytes())
            adapter.apply(root, self.config)
            self.assertIn('return rdgen_update::check();', (root / 'src/updater.rs').read_text())
            generated = (root / 'src/rdgen_update.rs').read_text()
            self.assertNotIn('@INSTALL_VERIFIED_UPDATE@', generated)
            if 'version = "1.5.1"' in (root / 'Cargo.toml').read_text():
                self.assertIn('&path, &release.sha256)', generated)
            after = (root / 'src/updater.rs').read_bytes()
            with self.assertRaises(ValueError):
                adapter.apply(root, self.config)
            self.assertEqual(after, (root / 'src/updater.rs').read_bytes())

    @unittest.skipIf(sys.platform == 'win32', 'Apache publication uses Linux file locking')
    def test_publication_is_monotonic_and_rejects_corrupt_files(self):
        from deploy import deploy
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prepare(self.source(root), root / 'bundle', 'StatusDesk', '1.5.0', '123', 'abc')
            deploy(root / 'bundle', root / 'public', public_download=True)
            channel = root / 'public/channels/statusdesk/test/windows-x64.json'
            previous = channel.read_bytes()
            catalog = json.loads((root / 'public/downloads.json').read_text())
            url = catalog['items']['windows-x64']['url']
            self.assertTrue(url.endswith('/windows-x64/2/client-windows-x64.exe'))
            public_file = root / 'public' / url.removeprefix('/client/')
            self.assertEqual(public_file.read_bytes(), (root / 'input/client.exe').read_bytes())
            with self.assertRaises(ValueError):
                deploy(root / 'bundle', root / 'public')
            (root / 'bundle/releases/statusdesk/test/windows-x64/2/client-windows-x64.exe').write_bytes(b'corrupted')
            with self.assertRaises(ValueError):
                deploy(root / 'bundle', root / 'public')
            self.assertEqual(previous, channel.read_bytes())

    @unittest.skipIf(sys.platform == 'win32', 'Apache publication uses Linux file locking')
    def test_new_upstream_base_replaces_channel_and_download_with_same_binary(self):
        from deploy import deploy
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self.source(root)
            receipt_path = source / 'stdesk-update-build.json'
            for version, revision in (('1.5.0.3', 281496451547139), ('1.5.1.1', 281496451612673)):
                receipt = json.loads(receipt_path.read_text())
                receipt.update(version=version, revision=revision)
                receipt_path.write_text(json.dumps(receipt))
                bundle = root / version
                prepare(source, bundle, 'StatusDesk', version, '123', 'abc')
                deploy(bundle, root / 'public', public_download=True)
            channel = load_manifest((root/'public/channels/statusdesk/test/windows-x64.json').read_bytes())
            catalog = json.loads((root/'public/downloads.json').read_text())['items']['windows-x64']
            self.assertEqual(channel['version'], '1.5.1.1')
            self.assertEqual(catalog['version'], channel['version'])
            self.assertIn('/'+str(channel['revision'])+'/', catalog['url'])
            self.assertEqual((root/'public'/catalog['url'].removeprefix('/client/')).read_bytes(), (source/'client.exe').read_bytes())

    @unittest.skipIf(sys.platform == 'win32', 'Apache publication uses Linux file locking')
    def test_x86_and_x64_same_revision_use_separate_files_and_channels(self):
        from deploy import deploy
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self.source(root)
            prepare(source, root / 'bundle64', 'StatusDesk', '1.5.0', '123', 'abc')
            deploy(root / 'bundle64', root / 'public', public_download=True)
            receipt_path = source / 'stdesk-update-build.json'
            receipt = json.loads(receipt_path.read_text())
            receipt['platform'] = 'windows-x86'
            receipt_path.write_text(json.dumps(receipt))
            binary = bytearray((source / 'client.exe').read_bytes())
            binary[132:134] = b'\x4c\x01'
            (source / 'client.exe').write_bytes(binary)
            prepare(source, root / 'bundle32', 'StatusDesk', '1.5.0', '124', 'abc')
            deploy(root / 'bundle32', root / 'public', public_download=True)
            catalog = json.loads((root / 'public/downloads.json').read_text())
            self.assertEqual(set(catalog['items']), {'windows-x64','windows-x86'})
            for platform in ('windows-x64','windows-x86'):
                channel = load_manifest((root / 'public/channels/statusdesk/test' / (platform + '.json')).read_bytes())
                file = root / 'public' / catalog['items'][platform]['url'].removeprefix('/client/')
                self.assertEqual(channel['platform'], platform)
                self.assertEqual(channel['filename'], file.name)


if __name__ == '__main__':
    unittest.main()
