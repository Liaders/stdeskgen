"""Desktop session titles from the authenticated accessible-device list."""
import json
from pathlib import Path


def apply(root):
    edits = {}

    def replace(name, old, new):
        path = root/name
        text = edits.get(path, path.read_text(encoding='utf-8'))
        if text.count(old) != 1:
            raise ValueError('Incompatible session title anchor: '+name)
        edits[path] = text.replace(old, new, 1)

    common = 'flutter/lib/common.dart'
    replace(common, "import 'dart:async';", "import 'dart:async';\nimport 'models/rdgen_session_title.dart';")
    replace(common, 'String getWindowNameWithId(String id, {WindowType? overrideType}) {', '''String getWindowNameWithId(String id, {WindowType? overrideType}) {
  if (isDesktop && (overrideType ?? kWindowType) == WindowType.RemoteDesktop) {
    final title = rdgenSessionTitle(id);
    if (title != null) return title;
  }''')
    replace(common, 'String getDesktopTabLabel(String peerId, String alias) {', '''String getDesktopTabLabel(String peerId, String alias) {
  if (isDesktop && kWindowType == WindowType.RemoteDesktop) {
    final title = rdgenSessionTitle(peerId);
    if (title != null) return title;
  }''')
    # A local option is shared by the main engine and remote-window engines.
    replace(common, 'String getWindowName({WindowType? overrideType}) {', '''String? rdgenSessionTitle(String id) {
  if (bind.mainGetLocalOption(key: 'rdgen-session-titles-v1') == 'N') return null;
  final token = bind.mainGetLocalOption(key: 'access_token');
  if (token.isEmpty) return null;
  try {
    final cache = jsonDecode(bind.mainGetLocalOption(key: 'rdgen-session-title-peers-v1'));
    if (cache is! Map || cache['access_token'] != token) return null;
    final peer = cache['peers'][id];
    if (peer is! Map) return null;
    return resolveSessionTitle(id, peer['alias'], peer['group']);
  } catch (_) {
    return null;
  }
}

String getWindowName({WindowType? overrideType}) {''')

    model = 'flutter/lib/models/group_model.dart'
    replace(model, '  Future<bool> _getPeers(List<Peer> tmpPeers) async {\n    try {', '''  Future<bool> _getPeers(List<Peer> tmpPeers) async {
    final titlePeers = <String, dynamic>{};
    final titleToken = bind.mainGetLocalOption(key: 'access_token');
    try {''')
    replace(model, '                final peer = PeerPayload.toPeer(peerPayload);', '''                final peer = PeerPayload.toPeer(peerPayload);
                titlePeers[peer.id] = {'alias': p['alias'], 'group': peer.device_group_name};''')
    replace(model, "      return true;\n    } catch (err) {\n      debugPrint('get accessible peers: $err');", '''      if (titleToken.isNotEmpty &&
          titleToken == bind.mainGetLocalOption(key: 'access_token')) {
        await bind.mainSetLocalOption(key: 'rdgen-session-title-peers-v1',
            value: jsonEncode({'access_token': titleToken, 'peers': titlePeers}));
      }
      return true;
    } catch (err) {
      debugPrint('get accessible peers: $err');''')
    settings = 'flutter/lib/desktop/pages/desktop_setting_page.dart'
    replace(settings, '      viewStyle(context),', '''      _Card(title: 'Interface', children: [
        _Checkbox(label: 'Use device aliases and groups in session titles',
          getValue: () => bind.mainGetLocalOption(key: 'rdgen-session-titles-v1') != 'N',
          setValue: (value) async {
            await bind.mainSetLocalOption(key: 'rdgen-session-titles-v1', value: value ? 'Y' : 'N');
          }),
      ]),
      viewStyle(context),''')
    translations = {'Interface': 'Интерфейс', 'Use device aliases and groups in session titles':
                    'Псевдонимы и группы устройств в заголовках сеансов'}
    for path in (root/'src/lang').glob('*.rs'):
        if path.name == 'en.rs':
            continue
        source = path.read_text(encoding='utf-8')
        anchor = '    ].iter().cloned().collect();'
        if source.count(anchor) != 1:
            raise ValueError('Incompatible session title translations: '+path.name)
        prefix, suffix = source.split(anchor)
        prefix = prefix.rstrip().removesuffix(',') + ','
        entries = ''.join('\n        ('+json.dumps(k)+', '+json.dumps(v if path.name == 'ru.rs' else '', ensure_ascii=False)+'),' for k, v in translations.items() if '"'+k+'"' not in source)
        edits[path] = prefix+entries+'\n'+anchor+suffix
    edits[root/'flutter/lib/models/rdgen_session_title.dart'] = Path(__file__).with_name('session_title.dart').read_text(encoding='utf-8')
    for path, text in edits.items():
        path.write_text(text, encoding='utf-8')
