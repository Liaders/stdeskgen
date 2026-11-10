import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from relay_retry import apply


class RelayRetryTests(unittest.TestCase):
    def test_existing_direct_only_hint_and_one_session_retry(self):
        source = Path(__file__).resolve().parents[2]/'rustdesk'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            originals = {}
            for name in ('src/client.rs', 'src/client/io_loop.rs', 'src/ui_session_interface.rs'):
                originals[name] = subprocess.check_output(['git', '-c', f'safe.directory={source.as_posix()}',
                    '-C', str(source), 'show', os.environ.get('RUSTDESK_TEST_REF', 'HEAD')+':'+name]).decode('utf-8')
                path = root/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(originals[name], encoding='utf-8')
            edits = {}
            apply(root, edits)
            client = edits[root/'src/client.rs']
            self.assertIn('if direct == Some(true)\n            && (', client)
            self.assertIn('cfg!(feature = "flutter") && rdgen_relay_retry::is_transport_error(&err)', client)
            self.assertIn('if !received {\n                relay_hint_type = "relay-hint2"', client)
            ui = edits[root/'src/ui_session_interface.rs']
            self.assertIn('lc.force_relay = true;', ui)
            self.assertIn('lc.policy_relay = true;\n            if !cfg!(feature = "flutter") {\n                lc.peer_relay = true;', ui)
            self.assertIn('on_establish_connection_error("Reset by the peer".to_owned())', edits[root/'src/client/io_loop.rs'])
            # Missing anchors reject the new base before any source is written.
            (root/'src/client/io_loop.rs').write_text('', encoding='utf-8')
            with self.assertRaises(ValueError):
                apply(root, {})
            self.assertEqual((root/'src/client.rs').read_text(encoding='utf-8'), originals['src/client.rs'])
