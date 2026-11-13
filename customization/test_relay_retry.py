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
            for name in ('flutter/lib/models/model.dart', 'src/lang/ru.rs', 'src/client.rs', 'src/client/io_loop.rs', 'src/ui/common.tis','src/ui_session_interface.rs'):
                originals[name] = subprocess.check_output(['git', '-c', f'safe.directory={source.as_posix()}',
                    '-C', str(source), 'show', os.environ.get('RUSTDESK_TEST_REF', 'HEAD')+':'+name]).decode('utf-8')
                path = root/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(originals[name], encoding='utf-8')
            edits = {}
            apply(root, edits)
            client = edits[root/'src/client.rs']
            self.assertIn('if direct == Some(true)\n            && (', client)
            self.assertIn('rdgen_relay_retry::is_transport_error(&err)', client)
            self.assertIn('handler.reconnect(true);', edits[root/'src/ui/common.tis'])
            self.assertIn('if (!rdgenAutoRelayTried', edits[root/'src/ui/common.tis'])
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
            self.assertNotIn("dialogButton('Always connect via relay'", dialog)
            self.assertEqual(dialog.count('dialogButton('), 2)
            self.assertIn("dialogButton('Retry directly'", dialog)
            self.assertIn('var rememberRelay = false;', dialog)
            self.assertIn('CheckboxListTile(', dialog)
            self.assertIn('if (rememberRelay) {', dialog)
            self.assertIn('await bind.mainSetPeerOption(id: peerId,', dialog)
            self.assertIn('value: bool2option(kOptionForceAlwaysRelay, true)', dialog)
            original_model = originals['flutter/lib/models/model.dart']
            self.assertIn('_rdgenAutoRelay.begin(text)', dialog)
            self.assertIn('unawaited(_rdgenRememberAutoRelay(peerId))', model)
            self.assertIn('if (!forceRelay) _rdgenAutoRelay.reset();', model)
            language = edits[root/'src/lang/ru.rs']
            self.assertIn('Подключиться через ретранслятор', language)
            self.assertNotIn('Подключится через ретранслятор', language)
            self.assertIn('Всегда использовать ретранслятор для этого устройства', language)
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

    @unittest.skipUnless(shutil.which('dart'), 'Dart SDK is available on CI')
    def test_automatic_retry_is_bounded_and_remembers_only_authenticated_relay(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'auto.dart'
            path.write_text(Path(__file__).with_name('auto_relay.dart').read_text(encoding='utf-8') + r'''
void check(bool value) { if (!value) throw StateError('Automatic relay policy'); }
void main() {
  final retry = RdgenAutoRelayRetry();
  for (final message in ['Wrong Password', 'Permission denied', 'Authentication timed out', 'Rejected', 'Offline']) {
    check(!retry.begin(message));
  }
  check(retry.begin('Reset by the peer'));
  check(!retry.begin('Connection timed out'));
  check(retry.authenticated(relayed: true));
  check(!retry.authenticated(relayed: true));
  retry.reset();
  check(retry.begin('Connection reset by peer (os error 104)'));
  check(!retry.authenticated(relayed: false));
  retry.reset();
  check(retry.begin('Connection timed out'));
  retry.pending = false; // A failed relay retry does not change device preferences.
  check(!retry.authenticated(relayed: true));
}
''', encoding='utf-8')
            subprocess.run(['dart', str(path)], check=True, timeout=60)
