import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))
from apply_version import apply
from disable_update_notifications import apply as disable_notifications


class ProductVersionTests(unittest.TestCase):
    def test_four_part_ui_and_file_version_keep_original_cargo_and_protocol(self):
        source = Path(__file__).resolve().parents[2] / 'rustdesk'
        def original(name):
            return subprocess.check_output(['git','-c',f'safe.directory={source.as_posix()}','-C',str(source),'show',os.environ.get('RUSTDESK_TEST_REF','HEAD')+':'+name])
        cargo = original('Cargo.toml')
        import re
        base = re.search(rb'^version = "([^"]+)"', cargo, re.M)[1].decode()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('src/ui_interface.rs','src/lang/ru.rs','src/client.rs','src/client/io_loop.rs','src/ui_session_interface.rs','src/hbbs_http/sync.rs','src/platform/windows.rs','build.py','flutter/pubspec.yaml','flutter/windows/runner/Runner.rc','build.rs','libs/portable/build.rs','Cargo.toml','src/common.rs'):
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(original(name))
            before=(root/'src/common.rs').read_text(encoding='utf-8')
            disable_notifications(root)
            after=(root/'src/common.rs').read_text(encoding='utf-8')
            anchor='pub async fn do_check_software_update() -> hbb_common::ResultType<()> {'
            self.assertEqual(before.split(anchor)[0], after.split(anchor)[0])
            self.assertEqual(before.split(anchor)[1].split('\n}',1)[1], after.split(anchor)[1].split('\n}',1)[1])
            self.assertTrue(after.split(anchor)[1].startswith('\n    Ok(())\n}'))
            apply(root,base,base+'.3')
            self.assertEqual((root/'Cargo.toml').read_bytes(),cargo)
            self.assertIn('"'+base+'.3".to_owned()', (root/'src/ui_interface.rs').read_text())
            sync = (root/'src/hbbs_http/sync.rs').read_text(encoding='utf-8')
            self.assertIn('v["version"] = json!(crate::ui_interface::get_version());', sync)
            self.assertEqual(sync.replace('v["version"] = json!(crate::ui_interface::get_version());',
                                          'v["version"] = json!(crate::VERSION);'),
                             original('src/hbbs_http/sync.rs').decode('utf-8'))
            self.assertIn('FILEVERSION', (root/'libs/portable/build.rs').read_text())
            self.assertIn('version: '+base+'+3', (root/'flutter/pubspec.yaml').read_text())
            namespace={}
            function=(root/'build.py').read_text().split('def get_version():',1)[1].split('\ndef ',1)[0]
            exec('def get_version():'+function,namespace)
            self.assertEqual(namespace['get_version'](),base+'.3')
