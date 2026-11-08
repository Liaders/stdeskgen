import hashlib
import importlib.util
import io
from pathlib import Path, PurePosixPath
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('restore_cortendesk', Path(__file__).with_name('restore-cortendesk.py'))
restore = importlib.util.module_from_spec(spec)
spec.loader.exec_module(restore)


class RestoreTests(unittest.TestCase):
    def test_checksum_detects_changed_backup(self):
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder)/'backup.tar.gz'
            archive.write_bytes(b'backup')
            Path(str(archive)+'.sha256').write_text(hashlib.sha256(b'backup').hexdigest()+'  backup.tar.gz\n')
            restore.verify_checksum(archive)
            archive.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                restore.verify_checksum(archive)

    def test_archive_escape_and_external_symlink_rejected(self):
        for name, link in [('../escape', None), ('secret-link', '/etc/passwd')]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                archive = root/'unsafe.tar'
                with tarfile.open(archive, 'w') as output:
                    member = tarfile.TarInfo(name)
                    if link:
                        member.type = tarfile.SYMTYPE
                        member.linkname = link
                    output.addfile(member)
                with self.assertRaises((ValueError, tarfile.FilterError)):
                    restore.extract(archive, root/'destination')
                self.assertFalse((root/'escape').exists())

    def test_container_preserves_identity_ports_and_uses_remapped_data(self):
        mount = {'Destination': '/data', 'RW': True}
        original = {'Config': {'Env': ['APP_KEY=fixture-secret', 'APP_URL=https://desk.status16.ru'],
                              'Cmd': ['start'], 'Entrypoint': ['/entrypoint'], 'Healthcheck': {'Test': ['CMD', 'true']}},
                    'HostConfig': {'PortBindings': {'8080/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '8080'}]},
                                   'RestartPolicy': {'Name': 'unless-stopped'}}}
        result = restore.make_spec(original, 'sha256:fixture-image', [(mount, PurePosixPath('/srv/new-data'))])
        self.assertEqual(result['Env'], original['Config']['Env'])
        self.assertEqual(result['HostConfig']['PortBindings'], original['HostConfig']['PortBindings'])
        self.assertEqual(result['HostConfig']['Binds'], ['/srv/new-data:/data:rw'])
        self.assertEqual(result['Image'], 'sha256:fixture-image')
        original['HostConfig']['Privileged'] = True
        with self.assertRaises(ValueError):
            restore.make_spec(original, 'image', [])


if __name__ == '__main__':
    unittest.main()
