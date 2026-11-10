import os
import shutil
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
            for name in ('flutter/lib/models/model.dart', 'src/lang/ru.rs', 'src/client.rs', 'src/client/io_loop.rs', 'src/ui_session_interface.rs'):
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
            model = edits[root/'flutter/lib/models/model.dart']
            start = model.index('  Future<void> showRelayHintDialog(')
            end = model.index('  void showConnectedWaitingForImage(', start)
            dialog = model[start:end]
            self.assertNotIn("dialogButton('Close'", dialog)
            self.assertIn('Icon(Icons.close)', dialog)
            self.assertIn('onCancel: onClose', dialog)
            self.assertIn('spacing: 12,\n              runSpacing: 12,', dialog)
            self.assertIn("dialogButton('Always connect via relay'", dialog)
            self.assertIn('await bind.mainSetPeerOption(id: peerId,', dialog)
            self.assertIn('value: bool2option(kOptionForceAlwaysRelay, true)', dialog)
            original_model = originals['flutter/lib/models/model.dart']
            self.assertEqual(model[:start], original_model[:original_model.index('  Future<void> showRelayHintDialog(')])
            self.assertEqual(model[end:], original_model[original_model.index('  void showConnectedWaitingForImage('):])
            language = edits[root/'src/lang/ru.rs']
            self.assertIn('Прямое подключение может оказаться невозможным.\\nВ этом случае рекомендуется подключиться через ретранслятор', language)
            if shutil.which('dart'):
                syntax = root/'relay-model-syntax.dart'
                syntax.write_text(model, encoding='utf-8')
                subprocess.run(['dart', 'format', '--output=none', str(syntax)], check=True, capture_output=True, timeout=60)
            # Missing anchors reject the new base before any source is written.
            (root/'src/client/io_loop.rs').write_text('', encoding='utf-8')
            with self.assertRaises(ValueError):
                apply(root, {})
            self.assertEqual((root/'src/client.rs').read_text(encoding='utf-8'), originals['src/client.rs'])
