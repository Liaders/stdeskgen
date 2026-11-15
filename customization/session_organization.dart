import 'package:flutter/material.dart';
import '../common.dart';
import 'rdgen_session_work_groups.dart';
import 'rdgen_session_work_groups_ui.dart';
import 'rdgen_organization_api.dart';
import 'rdgen_organization_editor.dart';

class RdgenSessionOrganization extends ChangeNotifier {
  WorkGroupSession? session;
  Map<String, dynamic>? snapshot;
  bool supported = false;
  bool dialogOpen = false;
  int menuDepth = 0;
  String? error;
  RdgenOrganizationApi? api;
  bool get interacting => dialogOpen || menuDepth > 0;
  bool get assigned => ['selected', 'automatic'].contains(snapshot?['status']);
  String? get name => assigned ? snapshot?['group']?['name'] as String? : null;
  int get additionalCount => api?.bindings.where((g) => g['id'] != snapshot?['group']?['id']).length ?? 0;
  bool get needsReminder => supported && !assigned && snapshot?['api_version'] == 2 &&
      snapshot?['device_has_organization'] == false;

  Future<void> attach(WorkGroupSession captured, OverlayDialogManager manager,
      bool Function() current, {bool preflightDone = false}) async {
    session = captured;
    api = RdgenOrganizationApi(captured.audit.replace(
      path: captured.audit.path.substring(0, captured.audit.path.length - '/api/audit/conn/active'.length),
      query: '', fragment: ''), captured.peerId, captured.requestAuthorized);
    snapshot = null;
    supported = false;
    error = null;
    notifyListeners();
    try {
      if (!await captured.resolve()) return;
      final fresh = await captured.read();
      if (!identical(session, captured) || !current()) return;
      snapshot = fresh;
      supported = fresh != null && fresh['status'] != null;
      notifyListeners();
      if (!supported) return;
      _syncCapabilities();
      if (assigned) {
        if (captured.preferredGroupId != null && fresh?['group']?['id'] != captured.preferredGroupId) {
          error = translate('The server recorded a different organization. Confirmed session assignments cannot be changed.');
          showToast(error!);
        }
        return;
      }
      final options = WorkGroupSession.choices(fresh!);
      final selected = captured.preferredChoice(options);
      if (selected != null && fresh['status'] == 'required') {
        await captured.select(selected);
        await refresh();
        if (!assigned && current()) await choose(manager, current);
      } else if (!preflightDone && current() && fresh['status'] == 'required') {
        await choose(manager, current);
      } else if (preflightDone && captured.preferredGroupId != null && current() && !assigned) {
        error = translate('Available organizations changed. Please choose again.');
        notifyListeners();
        await choose(manager, current);
      }
    } catch (_) {
      if (identical(session, captured)) {
        error = translate('Could not load the session organization');
        notifyListeners();
      }
    }
  }

  Future<void> refresh() async {
    final captured = session;
    if (captured == null) return;
    final fresh = await captured.read();
    if (!identical(captured, session)) return;
    snapshot = fresh;
    supported = fresh != null && fresh['status'] != null;
    _syncCapabilities();
    error = null;
    notifyListeners();
  }

  void _syncCapabilities() {
    if (api == null || snapshot?['api_version'] != 2) return;
    api!.version2 = true;
    api!.permissions = Map<String, dynamic>.from(snapshot?['permissions'] ?? {});
    api!.bindings = WorkGroupSession.choices({'groups': snapshot?['bindings'] ?? []});
  }

  Future<void> _save(int id, bool needsAttachment, {bool additional = false}) async {
    final captured = session;
    if (captured == null || api == null) throw StateError('Session unavailable');
    if (additional) {
      await api!.attach(id);
    } else {
      if (assigned && snapshot?['group']?['id'] != id) throw RdgenOrganizationApiError(409);
      final attach = needsAttachment || snapshot?['status'] == 'ungrouped';
      if (attach && (snapshot?['api_version'] != 2 ||
          snapshot?['permissions']?['can_attach_and_assign'] != true)) {
        throw RdgenOrganizationApiError(403);
      }
      final result = await captured.select(id, attachDevice: attach);
      if (result == null || !['selected', 'automatic'].contains(result['status'])) {
        await refresh();
        throw RdgenOrganizationApiError(422);
      }
    }
    await refresh();
    if (!additional && !assigned) throw StateError('Assignment not confirmed');
    if (!additional && snapshot?['group']?['id'] != id) throw RdgenOrganizationApiError(409);
  }

  Future<bool> beforeClose(OverlayDialogManager manager) async {
    if (!needsReminder || api == null || session == null) return false;
    if (dialogOpen) return true;
    dialogOpen = true;
    notifyListeners();
    try {
      final decision = await rdgenEditOrganization(manager: manager, api: api!,
        boundChoices: WorkGroupSession.choices(snapshot!), closing: true,
        loadBound: () async { await refresh(); return WorkGroupSession.choices(snapshot ?? {}); },
        save: (id, attach) => _save(id, attach));
      return decision == RdgenOrganizationDecision.cancel;
    } finally { dialogOpen = false; notifyListeners(); }
  }

  Future<void> choose(OverlayDialogManager manager, bool Function() current) async {
    final captured = session;
    if (captured == null || !supported || dialogOpen || !current()) return;
    dialogOpen = true;
    notifyListeners();
    try {
      if (assigned) {
        final add = await manager.show<bool>((setState, close, context) => CustomAlertDialog(
          title: Text(translate('Session organization')),
          content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(name ?? translate('Organization not selected')),
            if (error != null) Text(error!),
            const SizedBox(height: 8),
            ...api!.bindings.map((g) => Text(g['name'] as String)),
          ]),
          actions: [
            if (api?.version2 == true && api?.permissions['can_attach'] == true)
              TextButton(onPressed: () => close(true), child: Text(translate('Add organization'))),
            TextButton(onPressed: close, child: Text(translate('Close')))],
          onCancel: close));
        if (add == true && current()) {
          await rdgenEditOrganization(manager: manager, api: api!, boundChoices: [],
            additional: true, save: (id, _) => _save(id, true, additional: true));
        }
        return;
      }
      if (api?.version2 == true) {
        await rdgenEditOrganization(manager: manager, api: api!,
          boundChoices: WorkGroupSession.choices(snapshot!),
          loadBound: () async { await refresh(); return WorkGroupSession.choices(snapshot ?? {}); },
          origin: captured.preferredGroupId, save: (id, attach) => _save(id, attach));
      } else {
        await rdgenChooseWorkGroup(captured, manager, current,
            allowSkip: true, showUnassigned: true, onSaved: refresh, onDisconnect: () {});
      }
      if (current()) await refresh();
    } finally {
      dialogOpen = false;
      notifyListeners();
    }
  }
}
