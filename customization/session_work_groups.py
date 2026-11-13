"""Thin Flutter hooks for the Console whole-session work-group API (no Sciter)."""
import json
from pathlib import Path


def apply(root, desktop=True):
    edits = {}
    path = root/'flutter/lib/models/model.dart'
    source = path.read_text(encoding='utf-8')

    def replace(old, new):
        nonlocal source
        if source.count(old) != 1:
            raise ValueError('Incompatible session work-group hook: '+old[:100])
        source = source.replace(old, new, 1)

    replace("import 'dart:async';", "import 'dart:async';\nimport 'rdgen_session_work_groups.dart';\nimport 'rdgen_session_work_groups_ui.dart';")
    replace('  void _queryAuditGuid(String peerId) async {', '''  String? _rdgenWorkGroupConnectionId;
  int? rdgenPreferredWorkGroupId;

  WorkGroupSession? _rdgenCaptureWorkGroup(String peerId) {
    if (bind.isDisableAccount()) return null;
    final token = bind.mainGetLocalOption(key: 'access_token');
    final url = bind.sessionGetAuditServerSync(sessionId: sessionId, typ: 'conn/active');
    final connectionId = bind.sessionGetConnSessionId(sessionId: sessionId);
    final uri = Uri.tryParse(url);
    if (token.isEmpty || uri == null || url.isEmpty || connectionId.isEmpty ||
        connectionId == '0' || _rdgenWorkGroupConnectionId == connectionId) return null;
    _rdgenWorkGroupConnectionId = connectionId;
    final connectionType = switch (parent.target?.connType) {
      ConnType.fileTransfer => 1,
      ConnType.portForward => 2,
      ConnType.rdp => 2,
      ConnType.viewCamera => 3,
      ConnType.terminal => 4,
      _ => 0,
    };
    return WorkGroupSession(uri, peerId, connectionId, connectionType, token,
      (method, uri, capturedToken, body) async {
        final headers = {'Authorization': 'Bearer $capturedToken', 'Content-Type': 'application/json'};
        final response = method == 'PUT'
            ? await http.put(uri, headers: headers, body: body)
            : await http.get(uri, headers: headers);
        return WorkGroupReply(response.statusCode, response.body);
      }, () => !bind.isDisableAccount() &&
          bind.mainGetLocalOption(key: 'access_token') == token,
      preferredGroupId: rdgenPreferredWorkGroupId);
  }

  void _queryAuditGuid(String peerId) async {''')
    replace('  handlePeerInfo(Map<String, dynamic> evt, String peerId, bool isCache) async {', '''  handlePeerInfo(Map<String, dynamic> evt, String peerId, bool isCache) async {
    // Capture before this handler awaits anything; reconnects have different IDs.
    final workGroup = isCache ? null : _rdgenCaptureWorkGroup(peerId);''')
    replace('      tryUseAllMyDisplaysForTheRemoteSession(peerId);', '''      tryUseAllMyDisplaysForTheRemoteSession(peerId);
      final manager = parent.target?.dialogManager;
      if (workGroup != null && manager != null) {
        unawaited(rdgenChooseWorkGroup(workGroup, manager, () =>
            parent.target != null &&
            bind.sessionGetConnSessionId(sessionId: sessionId) == workGroup.connectionId));
      }''')
    edits[path] = source
    for name in ['session_work_groups', 'session_work_groups_ui']:
        edits[root/f'flutter/lib/models/rdgen_{name}.dart'] = Path(__file__).with_name(name+'.dart').read_text(encoding='utf-8')
    translations = {
        'Session organization': 'Организация сеанса',
        'Choose an organization for this session.': 'Выберите организацию для этого сеанса.',
        'Organization not selected': 'Организация не выбрана',
        'Available organizations changed. Please choose again.': 'Список организаций изменился. Выберите заново.',
        'Could not save the organization. Please try again.': 'Не удалось сохранить организацию. Повторите попытку.',
        'Selected from the current tab': 'Выбрана по текущей вкладке',
        'Do not select': 'Не выбирать',
    }
    for path in (root/'src/lang').glob('*.rs'):
        if path.name == 'en.rs':
            continue
        text = path.read_text(encoding='utf-8')
        anchor = '    ].iter().cloned().collect();'
        if text.count(anchor) != 1:
            raise ValueError('Incompatible work-group translations: '+path.name)
        prefix, suffix = text.split(anchor)
        entries = ''.join('\n        ('+json.dumps(k)+', '+json.dumps(v if path.name == 'ru.rs' else '', ensure_ascii=False)+'),' for k, v in translations.items() if '"'+k+'"' not in text)
        edits[path] = prefix.rstrip().removesuffix(',')+','+entries+'\n'+anchor+suffix
    for path, text in edits.items():
        path.write_text(text, encoding='utf-8')
    if desktop:
        from work_group_origin import apply as apply_origin
        apply_origin(root)
