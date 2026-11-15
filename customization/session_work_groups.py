"""Thin Flutter hooks for the Console whole-session work-group API (no Sciter)."""
import json
from pathlib import Path


def apply(root, desktop=True):
    if not desktop:
        from session_work_groups_legacy import apply as apply_legacy
        return apply_legacy(root, desktop=False)
    edits = {}
    path = root/'flutter/lib/models/model.dart'
    source = path.read_text(encoding='utf-8')

    def replace(old, new):
        nonlocal source
        if source.count(old) != 1:
            raise ValueError('Incompatible session work-group hook: '+old[:100])
        source = source.replace(old, new, 1)

    replace("import 'dart:async';", "import 'dart:async';\nimport 'rdgen_session_work_groups.dart';\nimport 'rdgen_session_work_groups_ui.dart';\nimport 'rdgen_session_organization.dart';")
    replace('  void _queryAuditGuid(String peerId) async {', '''  String? _rdgenWorkGroupConnectionId;
  int? rdgenPreferredWorkGroupId;
  bool rdgenPreflightDone = false;
  final rdgenOrganization = RdgenSessionOrganization();

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
        final headers = {'Authorization': 'Bearer $capturedToken', 'Content-Type': 'application/json', 'Accept': 'application/json'};
        final response = method == 'PUT'
            ? await http.put(uri, headers: headers, body: body)
            : await http.get(uri, headers: headers);
        return WorkGroupReply(response.statusCode, response.body,
            retryAfter: response.headers['retry-after']);
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
        unawaited(rdgenOrganization.attach(workGroup, manager, () =>
            parent.target != null &&
            bind.sessionGetConnSessionId(sessionId: sessionId) == workGroup.connectionId,
            preflightDone: rdgenPreflightDone));
      }''')
    edits[path] = source
    common = root/'flutter/lib/common.dart'
    common_source = common.read_text(encoding='utf-8')
    anchor = '  void dismissAll() {'
    if common_source.count(anchor) != 1: raise ValueError('Incompatible dialog manager')
    edits[common] = common_source.replace(anchor, '''  bool get rdgenHasOpenDialogs => _dialogs.isNotEmpty;

  void dismissAllExceptTag(String tag) {
    for (final key in _dialogs.keys.toList()) {
      if (key != tag) dismissByTag(key);
    }
  }

  void dismissAll() {''', 1)
    anchor = '      dialogManager.dismissAll();\n      try {\n        await canvasModel.updateViewStyle();'
    if source.count(anchor) != 1: raise ValueError('Incompatible first-image overlay cleanup')
    edits[path] = source.replace(anchor, '''      dialogManager.dismissAllExceptTag(
          'statusdesk-work-group-${bind.sessionGetConnSessionId(sessionId: sessionId)}');
      try {
        await canvasModel.updateViewStyle();''', 1)
    for name in ['session_work_groups', 'session_work_groups_ui', 'session_organization', 'organization_choices', 'organization_api', 'organization_editor']:
        edits[root/f'flutter/lib/models/rdgen_{name}.dart'] = Path(__file__).with_name(name+'.dart').read_text(encoding='utf-8')
    dialog = root/'flutter/lib/common/widgets/dialog.dart'
    dialog_source = dialog.read_text(encoding='utf-8')
    anchor = '''    {required FFI ffi, String? type, String? title, String? text}) async {
  final res = await _showConnEndAuditDialogCloseCanceled('''
    if dialog_source.count(anchor) != 1: raise ValueError('Incompatible intentional disconnect hook')
    edits[dialog] = dialog_source.replace(anchor, '''    {required FFI ffi, String? type, String? title, String? text}) async {
  if (type == null && bind.willSessionCloseCloseSession(sessionId: ffi.sessionId) &&
      await ffi.ffiModel.rdgenOrganization.beforeClose(ffi.dialogManager)) return true;
  final res = await _showConnEndAuditDialogCloseCanceled(''', 1)
    translations = {
        'Session organization': 'Организация сеанса',
        'Choose an organization for this session.': 'Выберите организацию для этого сеанса.',
        'Organization not selected': 'Организация не выбрана',
        'Available organizations changed. Please choose again.': 'Список организаций изменился. Выберите заново.',
        'Could not save the organization. Please try again.': 'Не удалось сохранить организацию. Повторите попытку.',
        'Selected from the current tab': 'Выбрана по текущей вкладке',
        'Do not select': 'Не выбирать',
        'Disconnect session': 'Отключиться',
        'Confirm': 'Подтвердить',
        'Assign organization': 'Назначить организацию',
        'Expand toolbar': 'Раскрыть панель',
        'Search organizations': 'Поиск организаций',
        'No organizations available': 'Нет доступных организаций',
        'Create organization…': 'Создать организацию…',
        'Organization creation requires a server API update': 'Для создания организации требуется обновление API сервера',
        'Assigning this device requires a server API update': 'Для назначения этому устройству организации требуется обновление API сервера',
        'Could not load the session organization': 'Не удалось получить организацию сеанса',
        'Session recording': 'Запись сеанса',
        'Add organization': 'Добавить организацию',
        'Organization operation is not permitted': 'Недостаточно прав для этой операции с организацией',
        'Please wait before retrying this organization operation': 'Подождите перед повторной попыткой',
        'Members of the selected user groups get access to the organization’s primary devices': 'Участники отмеченных групп пользователей получают доступ к основным устройствам организации',
        'Retry the pending creation to recover its result without duplicates': 'Повторите незавершённое создание, чтобы получить результат без дубликатов',
        'Organization creation requires permission from the server': 'Создание организации доступно только с разрешения сервера',
        'End without organization': 'Завершить без организации',
        'Return to session': 'Вернуться в сеанс',
        'Save and end session': 'Сохранить и завершить',
        'You are ending a session with a device without an organization. Select or create one to attribute this entire session to it.': 'Вы завершаете сеанс с устройством, которому не назначена организация. Рекомендуем выбрать организацию из списка или создать новую. После сохранения весь этот сеанс будет учитываться в отчётах по выбранной организации',
        'The server recorded a different organization. Confirmed session assignments cannot be changed.': 'Сервер записал другую организацию. Подтверждённую организацию сеанса изменить нельзя',
    }
    for path in (root/'src/lang').glob('*.rs'):
        if path.name == 'en.rs':
            continue
        text = path.read_text(encoding='utf-8')
        if path.name == 'ru.rs':
            text = text.replace('(\"Confirm\", \"\")', '(\"Confirm\", \"Подтвердить\")')
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
        from remote_toolbar import apply as apply_toolbar
        apply_toolbar(root)
