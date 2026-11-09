from pathlib import Path
import unittest
from publish_from_windows import putty_connection


class PublishConnectionTests(unittest.TestCase):
    def test_pin_used_for_shared_putty_arguments_without_disabling_batch(self):
        pin = 'SHA256:' + 'a'*43
        args = putty_connection(22, Path('private key.ppk'), pin)
        self.assertEqual(args, ['-batch', '-P', '22', '-i', 'private key.ppk', '-hostkey', pin])
        self.assertNotIn('-hostkey', putty_connection(22, 'key.ppk'))

    def test_unverified_or_wildcard_pin_rejected(self):
        for pin in ('*', '', 'SHA256:short', ['SHA256:'+'a'*43], 'SHA256:'+'a'*43+'\n'):
            with self.subTest(pin=pin), self.assertRaises(ValueError):
                putty_connection(22, 'key.ppk', pin)
