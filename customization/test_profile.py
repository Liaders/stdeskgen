import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('profile', Path(__file__).with_name('apply_profile.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ProfileTests(unittest.TestCase):
    def test_apply_and_reject_incompatible_sources_without_partial_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = Path(__file__).resolve().parents[2] / 'rustdesk'
            for name in ('common.dart', 'common/widgets/peer_tab_page.dart', 'common/widgets/my_group.dart', 'common/widgets/address_book.dart', 'models/group_model.dart', 'common/widgets/peer_card.dart'):
                target = root / 'flutter/lib' / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(subprocess.check_output(['git', '-c', f'safe.directory={source.as_posix()}', '-C', str(source), 'show', f'HEAD:flutter/lib/{name}']))
            profile = {'schema_version': 1, 'accent': '#123456', 'navigation': 'text', 'group_width': 280, 'device_names': True}
            module.apply(root, '1.5.0', profile)
            self.assertIn('accent = Color(0xFF123456)', (root / 'flutter/lib/common.dart').read_text())
            self.assertIn('width: 280,', (root / 'flutter/lib/common/widgets/my_group.dart').read_text())
            self.assertIn('child: Text(model.tabTooltip(t)', (root / 'flutter/lib/common/widgets/peer_tab_page.dart').read_text())
            before = {p: p.read_bytes() for p in root.rglob('*.dart')}
            with self.assertRaises(ValueError):
                module.apply(root, '1.5.0', profile)
            self.assertEqual(before, {p: p.read_bytes() for p in root.rglob('*.dart')})

    def test_unsupported_version_rejected(self):
        with self.assertRaisesRegex(ValueError, 'not supported'):
            module.apply(Path('.'), 'master', {'schema_version': 1})

    def test_invalid_profile_rejected(self):
        for profile in ({'schema_version': 2}, {'schema_version': 1, 'accent': 'red'}, {'schema_version': 1, 'group_width': -1}, {'schema_version': 1, 'device_aliases': True}, {'schema_version': 1, 'device_names': 'yes'}):
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                module.apply(Path('.'), '1.5.0', profile)


if __name__ == '__main__':
    unittest.main()



