"""Reuse RustDesk's relay hint for transport resets without an OS error number."""
from pathlib import Path
import json
import re


def apply(root, edits):
    def replace(name, old, new):
        path = root/name
        source = edits.get(path, path.read_text(encoding='utf-8'))
        if source.count(old) != 1:
            raise ValueError('Incompatible relay retry source: '+name)
        edits[path] = source.replace(old, new, 1)

    path = root/'src/client.rs'
    source = edits.get(path, path.read_text(encoding='utf-8'))
    if 'mod rdgen_relay_retry;' in source:
        raise ValueError('Relay retry already applied')
    edits[path] = 'mod rdgen_relay_retry;\n'+source
    replace('src/client.rs',
            '                || (!err.contains("Failed") && err.contains("deadline")))',
            '''                || (!err.contains("Failed") && err.contains("deadline"))
                || rdgen_relay_retry::is_transport_error(&err))''')
    replace('src/client.rs', 'if cfg!(feature = "flutter") && relay_hint {', 'if relay_hint {')
    replace('src/client/io_loop.rs',
            '                                    self.handler.msgbox("error", "Connection Error", "Reset by the peer", "");',
            '''                                    self.handler.on_establish_connection_error("Reset by the peer".to_owned());''')
    # Keep relay policy for this session, but don't mark the peer for persistence.
    replace('src/ui_session_interface.rs', '''            // An explicit retry-via-relay is a decision about this peer, not transport
            // necessity: Relay-only ICE for this round like any force-always-relay session,
            // and it is the one kind of relay that belongs in the peer's saved config.
            lc.policy_relay = true;
            lc.peer_relay = true;''', '''            lc.policy_relay = true;
            if !cfg!(feature = "flutter") {
                lc.peer_relay = true;
            }''')
    edits[root/'src/client/rdgen_relay_retry.rs'] = Path(__file__).with_name('relay_retry.rs').read_text(encoding='utf-8')
    sciter_hook = 'handler.msgbox_retry = function(type, title, text, link, hasRetry) {'
    sciter = root/'src/ui/common.tis'
    text = edits.get(sciter, sciter.read_text(encoding='utf-8'))
    if text.count(sciter_hook) != 1: raise ValueError('Incompatible Sciter relay retry hook')
    text = text.replace(sciter_hook, Path(__file__).with_name('auto_relay.tis').read_text(encoding='utf-8')+'\n'+sciter_hook+'''
    if (type == "relay-hint" || type == "relay-hint2") {
        if (!rdgenAutoRelayTried && rdgenRelayNetworkError(text)) {
            rdgenAutoRelayTried = true;
            self.timer(0, retryConnect);
            connecting();
            handler.reconnect(true);
            return;
        }
        type = "error";
    }''', 1)
    edits[sciter] = text
    model = root/'flutter/lib/models/model.dart'
    source = edits.get(model, model.read_text(encoding='utf-8'))
    start = source.index('  Future<void> showRelayHintDialog(')
    end = source.index('  void showConnectedWaitingForImage(', start)
    original = source[start:end]
    old_hint = '''    var hint = "\\n\\n${translate('relay_hint_tip')}";
    if (text.contains("10054") || text.contains("104")) {
      hint = "";
    }'''
    if original.count(old_hint) != 1: raise ValueError('Incompatible relay dialog hint')
    updated = original.replace(old_hint, '''    final hint = "\\n\\n${translate('relay_hint_tip')}";''', 1)
    show = "    dialogManager.show(tag: '$sessionId-$type', (setState, close, context) {"
    if updated.count(show) != 1: raise ValueError('Incompatible relay dialog state')
    updated = updated.replace(show, '    var rememberRelay = false;\n'+show, 1)
    dialog_start = updated.index('      return CustomAlertDialog(')
    dialog_end = updated.index('      );', dialog_start) + len('      );')
    dialog = Path(__file__).with_name('relay_dialog.dart').read_text(encoding='utf-8').rstrip()
    updated = updated[:dialog_start] + dialog + updated[dialog_end:]
    edits[model] = source[:start] + updated + source[end:]
    source = edits[model]
    source = "import 'rdgen_auto_relay.dart';\n" + source
    marker = '  Future<void> showRelayHintDialog('
    source = source.replace(marker, '''  final _rdgenAutoRelay = RdgenAutoRelayRetry();

  Future<void> _rdgenRememberAutoRelay(String peerId) async {
    if (!_rdgenAutoRelay.authenticated(relayed: direct == false)) return;
    try {
      await bind.mainSetPeerOption(id: peerId, key: kOptionForceAlwaysRelay,
          value: bool2option(kOptionForceAlwaysRelay, true));
    } catch (_) {
      debugPrint('Could not remember successful automatic relay retry');
    }
  }

  Future<void> showRelayHintDialog(''', 1)
    hook = '''      String peerId) async {
    final hint ='''
    if source.count(hook) != 1: raise ValueError('Incompatible automatic relay hook')
    source = source.replace(hook, '''      String peerId) async {
    // Native relay hints are emitted only after a failed direct transport.
    if (parent.target?.closed == false && _rdgenAutoRelay.begin(text)) {
      reconnect(dialogManager, sessionId, true);
      return;
    }
    _rdgenAutoRelay.pending = false;
    final hint =''', 1)
    hook = '      bool forceRelay) {\n'
    if source.count(hook) != 1: raise ValueError('Incompatible reconnect hook')
    source = source.replace(hook, hook+'    if (!forceRelay) _rdgenAutoRelay.reset();\n', 1)
    hook = '  handlePeerInfo(Map<String, dynamic> evt, String peerId, bool isCache) async {\n'
    if source.count(hook) != 1: raise ValueError('Incompatible relay authentication hook')
    source = source.replace(hook, hook+'    if (!isCache) unawaited(_rdgenRememberAutoRelay(peerId));\n', 1)
    hook = "    final link = evt['link'];"
    if source.count(hook) != 1: raise ValueError('Incompatible relay failure event')
    source = source.replace(hook, hook+"\n    if (type == 'error') _rdgenAutoRelay.pending = false;", 1)
    edits[model] = source
    edits[root/'flutter/lib/models/rdgen_auto_relay.dart'] = Path(__file__).with_name('auto_relay.dart').read_text(encoding='utf-8')
    language = root/'src/lang/ru.rs'
    source = edits.get(language, language.read_text(encoding='utf-8'))
    text = 'Прямое подключение может оказаться невозможным.\nВ этом случае рекомендуется подключиться через ретранслятор'
    entry = '('+json.dumps('relay_hint_tip')+', '+json.dumps(text, ensure_ascii=False)+')'
    source, count = re.subn(r'\("relay_hint_tip", "(?:\\.|[^"\\])*"\)', lambda _: entry, source)
    if count != 1: raise ValueError('Incompatible Russian relay hint')
    source, count = re.subn(r'\("Connect via relay", "(?:\\.|[^"\\])*"\)',
                            lambda _: '("Connect via relay", "Подключиться через ретранслятор")', source)
    if count != 1: raise ValueError('Incompatible Russian relay button')
    edits[language] = source
    translations = {'Retry directly': 'Повторить напрямую',
                    'Always use relay for this device': 'Всегда использовать ретранслятор для этого устройства'}
    for path in (root/'src/lang').glob('*.rs'):
        if path.name == 'en.rs': continue
        source = edits.get(path, path.read_text(encoding='utf-8'))
        missing = [key for key in translations if '"'+key+'"' not in source]
        if not missing: continue
        anchor = '    ].iter().cloned().collect();'
        if source.count(anchor) != 1: raise ValueError('Incompatible relay dialog translations: '+path.name)
        prefix, suffix = source.split(anchor)
        entries = ''.join('\n        ('+json.dumps(key)+', '+json.dumps(translations[key] if path.name == 'ru.rs' else '', ensure_ascii=False)+'),' for key in missing)
        edits[path] = prefix.rstrip().removesuffix(',')+','+entries+'\n'+anchor+suffix
