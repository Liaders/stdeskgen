import io
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest

from slim_ui import apply
from session_titles import apply as apply_titles
from apply_profile import apply as apply_profile


class SlimUiTests(unittest.TestCase):
    def fixture(self, root):
        source = Path(__file__).resolve().parents[2]/'rustdesk'
        data = subprocess.check_output(['git','-c',f'safe.directory={source.as_posix()}','-C',str(source),
            'archive',os.environ.get('RUSTDESK_TEST_REF','HEAD'),'flutter/lib','src/lang'])
        with tarfile.open(fileobj=io.BytesIO(data)) as archive:
            archive.extractall(root,filter='data')
        apply_titles(root)

    def test_optional_density_preserves_sidebar_fonts_and_coexists_with_profiles(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);self.fixture(root)
            home=root/'flutter/lib/desktop/pages/desktop_home_page.dart'
            original_sidebar=home.read_bytes()
            apply(root)
            self.assertEqual(home.read_bytes(),original_sidebar)
            connection=(root/'flutter/lib/desktop/pages/connection_page.dart').read_text(encoding='utf-8')
            self.assertIn('child: Text(translate("Connect"))',connection)
            self.assertIn('fontSize: 22,',connection)
            self.assertIn('rdgenSlimUi.value ? 8 : 22',connection)
            helper=(root/'flutter/lib/models/rdgen_slim_ui.dart').read_text(encoding='utf-8')
            self.assertIn("bind.mainGetLocalOption(key: rdgenSlimUiKey) == 'Y'",helper)
            self.assertIn('if (!rdgenSlimUi.value) return Column(children: children);',helper)
            self.assertIn('min(280.0, constraints.maxWidth)',helper)
            self.assertIn('https://desk.status16.ru/login',helper)
            self.assertIn('displayNameOrUserName',helper)
            self.assertIn('max(28.0, MediaQuery.textScalerOf(context)',connection)
            self.assertIn("value: value ? 'Y' : 'N'",helper)
            settings=(root/'flutter/lib/desktop/pages/desktop_setting_page.dart').read_text(encoding='utf-8')
            self.assertEqual(settings.count("_Card(title: 'Interface'"),1)
            self.assertIn('setValue: setRdgenSlimUi',settings)
            apply_profile(root,'1.5.1',{'schema_version':1,'navigation':'text','device_names':True,'colleagues':True,'resizable_panels':True})
            self.assertIn('rdgenSlimUi.value ? 3 : 6',(root/'flutter/lib/common/widgets/rdgen_colleagues.dart').read_text(encoding='utf-8'))
            if shutil.which('dart'):
                for name in ['desktop/pages/connection_page.dart','desktop/pages/desktop_setting_page.dart',
                             'common/widgets/peer_tab_page.dart','common/widgets/peers_view.dart',
                             'common/widgets/my_group.dart','common/widgets/rdgen_colleagues.dart','models/rdgen_slim_ui.dart']:
                    subprocess.run(['dart','format','--output=none',str(root/'flutter/lib'/name)],check=True,capture_output=True,timeout=60)

    def test_changed_upstream_layout_is_rejected_before_any_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);self.fixture(root)
            path=root/'flutter/lib/desktop/pages/connection_page.dart'
            source=path.read_text(encoding='utf-8')
            path.write_text(source.replace('width: 320 + 20 * 2,','width: 400,'),encoding='utf-8')
            before={p:p.read_bytes() for p in root.rglob('*') if p.is_file()}
            with self.assertRaisesRegex(ValueError,'remote-ID layout changed'):
                apply(root)
            self.assertEqual(before,{p:p.read_bytes() for p in root.rglob('*') if p.is_file()})
