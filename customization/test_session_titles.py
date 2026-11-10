import io
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest

from session_titles import apply
from apply_profile import apply as apply_profile


class SessionTitleTests(unittest.TestCase):
    def test_desktop_hooks_and_profile_coexist_on_supported_source(self):
        source = Path(__file__).resolve().parents[2]/'rustdesk'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = subprocess.check_output(['git', '-c', f'safe.directory={source.as_posix()}',
                '-C', str(source), 'archive', os.environ.get('RUSTDESK_TEST_REF', 'HEAD'),
                'flutter/lib', 'src/lang'])
            with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
                archive.extractall(root, filter='data')
            common = root/'flutter/lib/common.dart'
            original = common.read_text(encoding='utf-8')
            apply(root)
            patched = common.read_text(encoding='utf-8')
            # Both old bodies remain intact; the feature only adds early returns.
            for function, end in [('getDesktopTabLabel', 'sessionRefreshVideo'),
                                  ('getWindowNameWithId', 'Future<void> updateSystemWindowTheme')]:
                old = original[original.index('String '+function):original.index(end, original.index('String '+function))]
                self.assertIn(old[old.index('\n')+1:], patched)
            self.assertIn("if (title != null) return title;", patched)
            self.assertIn("cache['access_token'] != token", patched)
            self.assertIn("== 'N') return null", patched)
            group = (root/'flutter/lib/models/group_model.dart').read_text(encoding='utf-8')
            self.assertIn("titlePeers[peer.id] = {'alias': p['alias'], 'group': peer.device_group_name}", group)
            self.assertIn("titleToken == bind.mainGetLocalOption(key: 'access_token')", group)
            settings = (root/'flutter/lib/desktop/pages/desktop_setting_page.dart').read_text(encoding='utf-8')
            self.assertIn("value: value ? 'Y' : 'N'", settings)
            apply_profile(root, '1.5.1', {'schema_version': 1, 'device_names': True, 'navigation': 'text', 'colleagues': True})
            self.assertIn('rdgenSessionTitle(peerId)', common.read_text(encoding='utf-8'))
            for language in (root/'src/lang').glob('*.rs'):
                if language.name != 'en.rs':
                    self.assertIn('Use device aliases and groups in session titles', language.read_text(encoding='utf-8'))

    @unittest.skipUnless(shutil.which('dart'), 'Dart SDK is installed on the compatibility runner')
    def test_displayed_titles(self):
        with tempfile.TemporaryDirectory() as directory:
            test = Path(directory)/'titles.dart'
            test.write_text(Path(__file__).with_name('session_title.dart').read_text(encoding='utf-8')+r'''
void main() {
  final cases = [
    ['123456', 'Office', 'Support', 'Office (Support)'],
    ['123456', '', 'Support', '123456 (Support)'],
    ['123456', 'Office', '', '123456 (Office)'],
    ['123456', '', '', null],
    ['123456', null, null, null],
    ['123456', '  Office  ', '  Support  ', 'Office (Support)'],
  ];
  for (final c in cases) {
    final actual = resolveSessionTitle(c[0] as String, c[1], c[2]);
    if (actual != c[3]) throw StateError('$actual != ${c[3]}');
  }
}
''', encoding='utf-8')
            subprocess.run(['dart', str(test)], check=True, timeout=60)
