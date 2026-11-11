import tempfile
import unittest
from pathlib import Path

from ubuntu_apt import configure


class AptMirrorTests(unittest.TestCase):
    def test_failed_mirror_is_removed_and_trust_and_suites_are_preserved(self):
        for modern in (True, False):
            with self.subTest(modern=modern), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root/'apt.conf.d').mkdir()
                (root/'sources.list.d').mkdir()
                (root/'apt-mirrors.txt').write_text('https://archive.ubuntu.com/ubuntu/\n')
                path = root/'sources.list.d/ubuntu.sources' if modern else root/'sources.list'
                trust = 'Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg'
                path.write_text('Types: deb\nURIs: mirror+file:/etc/apt/apt-mirrors.txt\nSuites: noble noble-security\n'+trust+'\n'
                    if modern else 'deb [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] http://azure.archive.ubuntu.com/ubuntu/ jammy main universe\n')
                selected = configure(root, 'noble' if modern else 'jammy',
                    probe=lambda uri, _: uri in ('https://azure.archive.ubuntu.com/ubuntu/', 'https://mirrors.edge.kernel.org/ubuntu/'))
                self.assertEqual(len(selected), 2)
                self.assertNotIn('https://archive.ubuntu.com/', (root/'apt-mirrors.txt').read_text())
                self.assertIn('ubuntu-archive-keyring.gpg', path.read_text())
                self.assertIn('noble noble-security' if modern else 'jammy main universe', path.read_text())
                self.assertIn('mirror+file:'+root.as_posix(),path.read_text())
                self.assertIn('Error-Mode "any"', (root/'apt.conf.d/80rdgen-network').read_text())

    def test_total_outage_fails_before_changing_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            path=root/'apt-mirrors.txt'
            path.write_text('https://archive.ubuntu.com/ubuntu/\n')
            before=path.read_bytes()
            with self.assertRaisesRegex(RuntimeError,'No reachable'):
                configure(root,'noble',probe=lambda *_: False)
            self.assertEqual(path.read_bytes(),before)
            self.assertFalse((root/'apt.conf.d/80rdgen-network').exists())


if __name__ == '__main__': unittest.main()
