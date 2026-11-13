import io
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest

from peer_password_menu import apply


class PasswordMenuTests(unittest.TestCase):
    def test_existing_action_in_each_device_menu_without_duplicate_address_book_entry(self):
        source = Path(__file__).resolve().parents[2]/'rustdesk'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = subprocess.check_output(['git', '-c', f'safe.directory={source.as_posix()}',
                '-C', str(source), 'archive', os.environ.get('RUSTDESK_TEST_REF', 'HEAD'),
                'flutter/lib/common/widgets/peer_card.dart'])
            with tarfile.open(fileobj=io.BytesIO(data)) as archive:
                archive.extractall(root, filter='data')
            path = root/'flutter/lib/common/widgets/peer_card.dart'
            original = path.read_text(encoding='utf-8')
            apply(root)
            text = path.read_text(encoding='utf-8')
            for name in ['RecentPeerCard', 'FavoritePeerCard', 'DiscoveredPeerCard', 'AddressBookPeerCard', 'MyGroupPeerCard']:
                start = text.index('class '+name+' extends BasePeerCard')
                end = text.find('\nclass ', start+1)
                body = text[start:end if end >= 0 else None]
                self.assertIn('await bind.mainPeerHasPassword(id: peer.id)', body)
                self.assertIn('menuItems.add(_unrememberPasswordAction(peer.id));', body)
            self.assertIn('!(gFFI.abModel.current.canWrite() && gFFI.abModel.current.isPersonal() && peer.hash.isNotEmpty)', text)
            start = original.index('  MenuEntryBase<String> _unrememberPasswordAction')
            end = original.index('\n  @protected', start)
            self.assertIn(original[start:end], text)
            if shutil.which('dart'):
                subprocess.run(['dart', 'format', '--output=none', str(path)], check=True, capture_output=True, timeout=60)
