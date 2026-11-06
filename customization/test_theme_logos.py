import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from theme_logos import stage, LOGOS

class ThemeLogoTests(unittest.TestCase):
    def test_distinct_logos_and_missing_variant_fallback(self):
        for supplied in ({'logo.png':b'common','logo_light.png':b'light','logo_dark.png':b'dark'},
                         {'logo.png':b'common','logo_dark.png':b'dark'},
                         {'logo_light.png':b'light'}, {}):
            with self.subTest(supplied=supplied), tempfile.TemporaryDirectory() as directory:
                root=Path(directory);assets=root/'input';assets.mkdir();target=root/'assets'
                for name,data in supplied.items():(assets/name).write_bytes(data)
                stage(assets,target)
                if not supplied:
                    self.assertFalse(target.exists());continue
                fallback=next(supplied[name] for name in LOGOS if name in supplied)
                for name in LOGOS:
                    self.assertEqual((target/name).read_bytes(),supplied.get(name,fallback))
                    self.assertEqual((assets/name).read_bytes(),(target/name).read_bytes())
                stage(assets,target)  # Packaging again must preserve distinct variants.
                for name,data in supplied.items():self.assertEqual((target/name).read_bytes(),data)

    def test_supported_flutter_source_switches_logo_with_current_theme(self):
        source=Path(__file__).resolve().parents[2]/'rustdesk'
        ref=os.environ.get('RUSTDESK_TEST_REF','HEAD')
        def original(name):
            return subprocess.check_output(['git','-c',f'safe.directory={source.as_posix()}','-C',str(source),'show',ref+':'+name]).decode('utf-8')
        common=original('flutter/lib/common.dart')
        for name in LOGOS:self.assertIn('assets/'+name,common)
        self.assertIn('Theme.of(context).brightness',common)
        self.assertIn('? [_kDarkLogoAsset, _kDefaultLogoAsset]',common)
        self.assertIn(': [_kLightLogoAsset, _kDefaultLogoAsset]',common)
        self.assertIn('- assets/',original('flutter/pubspec.yaml'))
