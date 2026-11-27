from pathlib import Path
import tempfile
import unittest

import test_slim_ui
from winter_mode import apply


class WinterModeTests(unittest.TestCase):
    def test_desktop_sidebar_keeps_original_controls_and_stages_selected_art(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            test_slim_ui.SlimUiTests().fixture(root)
            home = root / 'flutter/lib/desktop/pages/desktop_home_page.dart'
            original = home.read_text(encoding='utf-8')
            apply(root)
            updated = home.read_text(encoding='utf-8')
            self.assertEqual(original.split('  buildIDBoard(', 1)[1],
                             updated.split('  buildIDBoard(', 1)[1])
            self.assertIn('RdgenWinterPane(builder: buildLeftPane)', updated)
            settings = (root / 'flutter/lib/desktop/pages/desktop_setting_page.dart').read_text(encoding='utf-8')
            self.assertEqual(settings.count("_Card(title: 'Interface'"), 1)
            self.assertIn("_Checkbox(label: 'New Year mode'", settings)
            helper = (root / 'flutter/lib/models/rdgen_winter_mode.dart').read_text(encoding='utf-8')
            self.assertIn("bind.mainGetLocalOption(key: rdgenWinterModeKey) == 'Y'", helper)
            self.assertIn('MyTheme.darkTheme.copyWith(', helper)
            for asset in Path(__file__).with_name('winter_assets').glob('*.png'):
                self.assertEqual(asset.read_bytes(), (root / 'flutter/assets' / asset.name).read_bytes())
            ru = (root / 'src/lang/ru.rs').read_text(encoding='utf-8')
            self.assertIn('("New Year mode", "Новогодний режим")', ru)


if __name__ == '__main__':
    unittest.main()
