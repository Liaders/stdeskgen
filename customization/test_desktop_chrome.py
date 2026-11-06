import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from desktop_chrome import apply_flutter, apply_sciter


class DesktopChromeTests(unittest.TestCase):
    def original(self,name):
        root=Path(__file__).resolve().parents[2]/'rustdesk'
        return subprocess.check_output(['git','-c',f'safe.directory={root.as_posix()}','-C',str(root),
            'show',os.environ.get('RUSTDESK_TEST_REF','HEAD')+':'+name])

    def test_desktop_id_actions_match_settings_tab_and_keep_mobile_branding(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name in ['flutter/lib/common.dart','flutter/lib/desktop/pages/desktop_home_page.dart']:
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(self.original(name))
            apply_flutter(root)
            common=(root/'flutter/lib/common.dart').read_text(encoding='utf-8')
            home=(root/'flutter/lib/desktop/pages/desktop_home_page.dart').read_text(encoding='utf-8')
            self.assertIn('if (isDesktop || bind.mainGetBuildinOption',common)
            self.assertIn('translate("powered_by_me")',common)
            tab=self.original('flutter/lib/desktop/pages/desktop_tab_page.dart').decode()
            self.assertIn('unselectedIcon: Icons.build_outlined',tab)
            self.assertIn('Icons.build_outlined,',home)
            self.assertNotIn('Icons.more_vert_outlined,',home)
            self.assertIn('Icons.content_copy',home)
            self.assertIn('ClipboardData(text: id)',home)
            self.assertIn('ClipboardData(text: model.serverId.text)',home)

    def test_sciter_only_removes_the_powered_by_row(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'src/ui/index.tis';path.parent.mkdir(parents=True)
            original=self.original('src/ui/index.tis').decode();path.write_text(original,encoding='utf-8')
            apply_sciter(root)
            expected=''.join(line for line in original.splitlines(keepends=True) if "translate('powered_by_me')" not in line)
            self.assertEqual(path.read_text(encoding='utf-8'),expected)
