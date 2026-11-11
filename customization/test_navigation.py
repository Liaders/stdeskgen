import io
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

from apply_profile import apply


class NavigationTests(unittest.TestCase):
    def fixture(self, root):
        source = Path(__file__).resolve().parents[2]/'rustdesk'
        raw = subprocess.check_output(['git', '-c', f'safe.directory={source.as_posix()}', '-C', str(source),
            'archive', os.environ.get('RUSTDESK_TEST_REF', 'HEAD'),
            'flutter/lib/common/widgets/peer_tab_page.dart', 'src/lang'])
        with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
            archive.extractall(root, filter='data')

    def test_both_initial_modes_use_saved_choice_and_existing_toolbar(self):
        for mode in ('text', 'icons'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.fixture(root)
                apply(root, '1.5.1', {'schema_version': 1, 'navigation': mode})
                page = (root/'flutter/lib/common/widgets/peer_tab_page.dart').read_text(encoding='utf-8')
                self.assertIn('bool _rdgenTextTabs = '+('true' if mode == 'text' else 'false')+';', page)
                self.assertIn("if (saved == 'text' || saved == 'icons') _rdgenTextTabs = saved == 'text';", page)
                self.assertEqual(page.count("'rdgen-navigation-style-v1'"), 2)
                self.assertIn("v: value ? 'text' : 'icons'", page)
                self.assertIn('if (isDesktop) _rdgenNavigationSwitch(),\n      _createPeerViewTypeSwitch(context),', page)
                self.assertIn('child: (isDesktop && _rdgenTextTabs', page)
                self.assertIn('Transform.translate(offset: const Offset(0, 5)',page)
                self.assertIn(': Icon(model.tabIcon(t), color: color))',page)
                self.assertIn('Icons.apps_rounded : Icons.text_fields_rounded, size: 18', page)
                self.assertEqual(page.count('Widget _rdgenNavigationSwitch()'), 1)
                ru = (root/'src/lang/ru.rs').read_text(encoding='utf-8')
                self.assertIn('Показывать значки вкладок', ru)
                for file in (root/'src/lang').glob('*.rs'):
                    if file.name != 'en.rs':
                        self.assertIn('"Show tab icons"', file.read_text(encoding='utf-8'))

    def test_mobile_adapter_can_opt_out_without_changing_peer_navigation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            path = root/'flutter/lib/common/widgets/peer_tab_page.dart'
            before = path.read_bytes()
            apply(root, '1.5.1', {'schema_version': 1}, desktop_navigation=False)
            self.assertEqual(path.read_bytes(), before)
