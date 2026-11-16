"""Validate generated translation modules without building RustDesk."""
import io
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest

from session_work_groups import apply
from session_titles import apply as apply_titles
from desktop_ui import apply as apply_desktop
from apply_profile import apply as apply_profile


class GeneratedTranslationsTests(unittest.TestCase):
    def test_generated_translation_modules(self):
        source = Path(__file__).resolve().parents[2] / 'rustdesk'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = subprocess.check_output([
                'git', '-c', f'safe.directory={source.as_posix()}', '-C', str(source),
                'archive', os.environ.get('RUSTDESK_TEST_REF', 'HEAD'), 'flutter/lib', 'src/lang'])
            with tarfile.open(fileobj=io.BytesIO(archive)) as data:
                data.extractall(root, filter='data')
            apply(root)
            apply_titles(root)
            apply_desktop(root, {'slim_ui': True})
            apply_profile(root, '1.5.1', {'schema_version': 1, 'device_names': True,
                'colleagues': True, 'organizations': True})
            modules = sorted(p for p in (root / 'src/lang').glob('*.rs') if p.name != 'en.rs')
            self.assertGreater(len(modules), 40)
            for module in modules:
                text = module.read_text(encoding='utf-8')
                with self.subTest(language=module.stem):
                    self.assertIn('("Create organization…",', text)
                    self.assertIn('organization’s primary devices",', text)
                    self.assertNotRegex(text, r'(?<!\\)\\u[0-9a-fA-F]{4}',
                        'JSON Unicode escape is invalid in a Rust string literal')
            self.assertIn('("Create organization…", "Создать организацию…")',
                (root / 'src/lang/ru.rs').read_text(encoding='utf-8'))
            compiler = shutil.which('rustc')
            if compiler is None:
                if os.environ.get('CI') == 'true':
                    self.fail('rustc is required for CI translation validation')
                print('Rust translation escape checks passed; rustc is unavailable locally.')
                return
            # Preserve every original module verbatim, replacing only lazy_static's
            # dependency with a tiny macro so rustc can check syntax and types.
            harness = root / 'translations_check.rs'
            harness.write_text('''#![allow(dead_code)]
extern crate self as lazy_static;
#[macro_export]
macro_rules! lazy_static {
    (pub static ref $name:ident: $ty:ty = $value:expr;) => {
        pub fn translations() -> $ty { $value }
    };
}
''' + '\n'.join(f'#[path = "{p.as_posix()}"] mod lang_{i};'
                for i, p in enumerate(modules)), encoding='utf-8')
            result = subprocess.run([compiler, '--edition=2021', '--crate-type=lib',
                '--emit=metadata', str(harness), '-o', str(root / 'translations.rmeta')],
                capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
            self.assertEqual(result.returncode, 0, result.stderr[-12000:])
            print(f'rustc checked {len(modules)} generated translation modules; no client build.')


if __name__ == '__main__':
    unittest.main()
