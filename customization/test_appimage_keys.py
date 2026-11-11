import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.request import urlretrieve

from appimage_keys import FINGERPRINTS, prepare


class AppImageKeyTests(unittest.TestCase):
    def recipe(self, root):
        source=Path(__file__).resolve().parents[2]/'rustdesk'
        original=subprocess.check_output(['git','-c',f'safe.directory={source.as_posix()}',
            '-C',str(source),'show',os.environ.get('RUSTDESK_TEST_REF','HEAD')+':appimage/AppImageBuilder-aarch64.yml'])
        recipe=root/'recipe.yml'; recipe.write_bytes(original)
        keyring=root/'ubuntu.gpg'; keyring.write_bytes(b'test installed keyring')
        return recipe,keyring

    def test_local_public_key_uri_works_without_keyserver_and_recipe_payload_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); recipe,keyring=self.recipe(root)
            before=recipe.read_text(encoding='utf-8')
            key=b'-----BEGIN PGP PUBLIC KEY BLOCK-----\ntest export\n'
            fingerprints='\n'.join('fpr:::::::::'+fp+':' for fp in FINGERPRINTS)
            output=root/'public key.asc'
            with patch('appimage_keys.subprocess.run',side_effect=[SimpleNamespace(stdout=fingerprints),SimpleNamespace(stdout=key)]):
                uri=prepare(recipe,output,keyring)
            after=recipe.read_text(encoding='utf-8')
            self.assertNotIn('keyserver.ubuntu.com',after)
            self.assertEqual(after.count(uri),4)
            self.assertIn('allow_unauthenticated: false',after)
            self.assertIn('https://ports.ubuntu.com/ubuntu-ports/',after)
            self.assertEqual(before[before.index('    include:'):],after[after.index('    include:'):])
            copied=root/'copied.asc'; urlretrieve(uri,str(copied))
            self.assertEqual(copied.read_bytes(),key)

    def test_wrong_key_fingerprint_fails_before_modifying_recipe(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); recipe,keyring=self.recipe(root)
            before=recipe.read_bytes(); output=root/'public.asc'
            with patch('appimage_keys.subprocess.run',return_value=SimpleNamespace(stdout='fpr:::::::::WRONG:')) as run:
                with self.assertRaisesRegex(ValueError,'fingerprint mismatch'):
                    prepare(recipe,output,keyring)
                self.assertEqual(run.call_count,1)
            self.assertEqual(recipe.read_bytes(),before)
            self.assertFalse(output.exists())
