import 'package:flutter/material.dart';
import '../common.dart';
import 'rdgen_organization_api.dart';
import 'rdgen_organization_choices.dart';

enum RdgenOrganizationDecision { saved, skip, cancel }

String rdgenOrganizationError(Object error) {
  if (error is RdgenOrganizationApiError) {
    if (error.status == 401 || error.status == 403) return translate('Organization operation is not permitted');
    if (error.status == 429) return translate('Please wait before retrying this organization operation');
    if (error.status == 409 || error.status == 422) return translate('Available organizations changed. Please choose again.');
  }
  return translate('Could not save the organization. Please try again.');
}

Future<Map<String, dynamic>?> rdgenCreateOrganization(
    OverlayDialogManager manager, RdgenOrganizationApi api, {bool Function()? active}) async {
  final options = await api.creationOptions();
  if (active != null && !active()) return null;
  final fields = options['fields'] as Map;
  final groups = (options['user_groups'] as List).cast<Map<String, dynamic>>();
  final pending = api.pendingCreate?.data;
  final name = TextEditingController(text: pending?['name'] as String? ?? '');
  final note = TextEditingController(text: pending?['note'] as String? ?? '');
  final selected = Set<int>.from((pending?['user_group_ids'] ?? options['default_user_group_ids']) as List);
  var busy = false;
  var closed = false;
  String? error;
  try {
    return await manager.show<Map<String, dynamic>>((setState, close, context) {
      void cancel() { closed = true; close(); }
      Future<void> submit({bool assign = false}) async {
        if (busy || name.text.trim().isEmpty) return;
        setState(() { busy = true; error = null; });
        try {
          final ids = selected.toList()..sort();
          final created = await api.create({'name': name.text.trim(),
            'note': note.text.trim().isEmpty ? null : note.text.trim(), 'user_group_ids': ids});
          if (!closed && context.mounted) { closed = true; close({...created, '_rdgen_assign': assign}); }
        } catch (failure) {
          if (failure is RdgenOrganizationApiError && failure.status == 422) api.pendingCreate = null;
          if (!closed && context.mounted) setState(() { error = rdgenOrganizationError(failure); });
        } finally {
          if (!closed && context.mounted) setState(() { busy = false; });
        }
      }
      final locked = busy || api.pendingCreate != null;
      return CustomAlertDialog(title: Text(translate('Create organization…')),
        content: _RdgenDialogLifetime(controllers: [name, note], child: SizedBox(width: 420, child: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(controller: name, enabled: !locked, maxLength: fields['name']['max_length'] as int,
            decoration: InputDecoration(labelText: translate('Name')),
            onChanged: (_) => setState(() {})),
          TextField(controller: note, enabled: !locked, maxLength: fields['note']['max_length'] as int,
            decoration: InputDecoration(labelText: translate('Note'))),
          Text(translate('Members of the selected user groups get access to the organization’s primary devices')),
          ...groups.map((g) => CheckboxListTile(title: Text(g['name'] as String),
            value: selected.contains(g['id']), onChanged: locked ? null : (value) => setState(() {
              if (value == true) selected.add(g['id'] as int); else selected.remove(g['id']);
            }))),
          if (api.pendingCreate != null && !busy)
            Text(translate('Retry the pending creation to recover its result without duplicates')),
          if (busy) const LinearProgressIndicator(),
          if (error != null) Text(error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
        ])))),
        actions: [TextButton(onPressed: busy ? null : cancel, child: Text(translate('Cancel'))),
          OutlinedButton(onPressed: busy || name.text.trim().isEmpty ? null : () => submit(),
            child: Text(translate(api.pendingCreate == null ? 'Create' : 'Retry'))),
          ElevatedButton(onPressed: busy || name.text.trim().isEmpty ? null : () => submit(assign: true),
            child: Text(translate('Create and assign')))],
        onCancel: busy ? null : cancel);
    });
  } finally { closed = true; }
}

Future<RdgenOrganizationDecision> rdgenEditOrganization({
  required OverlayDialogManager manager, required RdgenOrganizationApi api,
  required List<Map<String, dynamic>> boundChoices,
  required Future<void> Function(int groupId, bool needsAttachment) save,
  Future<List<Map<String, dynamic>>> Function()? loadBound,
  bool Function()? assignmentConfirmed,
  int? origin, bool closing = false, bool additional = false, bool reconnecting = false,
}) async {
  final byId = {for (final group in boundChoices) group['id'] as int: group};
  var bound = List<Map<String, dynamic>>.of(boundChoices);
  int? selected = byId.containsKey(origin) ? origin : null;
  var busy = true;
  var mutating = false;
  var confirming = false;
  var authorizationFailed = false;
  var started = false;
  var disposed = false;
  String? error;
  final alias = TextEditingController();
  final offerAlias = boundChoices.isEmpty && !additional && api.canSetAlias && api.alias == '';
  try {
    final result = await manager.show<RdgenOrganizationDecision>((setState, close, context) {
      void finish(RdgenOrganizationDecision decision) { disposed = true; close(decision); }
      Future<void> load() async {
        setState(() { busy = true; });
        try {
          if (loadBound != null) bound = await loadBound();
          if (assignmentConfirmed?.call() == true) {
            if (!disposed && context.mounted) finish(RdgenOrganizationDecision.saved);
            return;
          }
          final available = await api.search();
          if (disposed || !context.mounted) return;
          setState(() {
            byId.clear();
            for (final group in bound) { byId[group['id'] as int] = group; }
            for (final group in available) { byId[group['id'] as int] = group; }
            if (!byId.containsKey(selected)) selected = null;
            if (selected == null && origin != null && byId.containsKey(origin)) selected = origin;
            error = null;
            authorizationFailed = false;
          });
        } catch (failure) {
          if (disposed || !context.mounted) return;
          if (failure is RdgenOrganizationApiError && [401,403].contains(failure.status)) authorizationFailed = true;
          if (!(failure is RdgenOrganizationApiError && !api.version2 && [404,405,501].contains(failure.status))) {
            setState(() { error = rdgenOrganizationError(failure); });
          }
        } finally { if (!disposed && context.mounted) setState(() { busy = false; }); }
      }
      if (!started) { started = true; Future.microtask(load); }
      Future<void> submit() async {
        if (busy || confirming || selected == null) return;
        final selectedId = selected!;
        final selectedName = byId[selectedId]?['name'] as String? ?? '$selectedId';
        confirming = true;
        final confirmed = closing || await rdgenConfirmOrganization(manager, selectedName, reconnecting: reconnecting);
        confirming = false;
        if (!confirmed || disposed || !context.mounted) return;
        setState(() { busy = true; mutating = true; error = null; });
        try {
          if (offerAlias && alias.text.trim().isNotEmpty && api.alias != alias.text.trim()) await api.saveAlias(alias.text);
          final needsAttachment = !bound.any((g) => g['id'] == selected);
          await save(selectedId, needsAttachment);
          if (!disposed && context.mounted) finish(RdgenOrganizationDecision.saved);
        } catch (failure) {
          if (!disposed && context.mounted) setState(() { error = rdgenOrganizationError(failure); });
          if (failure is RdgenOrganizationApiError && [409,422].contains(failure.status)) await load();
        } finally { if (!disposed && context.mounted) setState(() { busy = false; mutating = false; }); }
      }
      Future<void> create() async {
        if (busy) return;
        var created = false;
        setState(() { busy = true; });
        try {
          final group = await rdgenCreateOrganization(manager, api, active: () => !disposed && context.mounted);
          if (disposed || !context.mounted) return;
          if (group != null) { created = group['_rdgen_assign'] == true; setState(() { byId[group['id'] as int] = group; selected = created ? group['id'] as int : null; error = null; }); }
        } catch (failure) { if (!disposed && context.mounted) setState(() { error = rdgenOrganizationError(failure); }); }
        finally { if (!disposed && context.mounted) setState(() { busy = false; }); }
        if (created && !disposed && context.mounted) await submit();
      }
      final groups = byId.values.toList()..sort((a,b) => (a['name'] as String).compareTo(b['name'] as String));
      return CustomAlertDialog(title: Text(translate(closing ? 'Session organization' : 'Assign organization')),
        content: _RdgenDialogLifetime(controllers: [alias], child: SizedBox(width: 420, child: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, children: [
          if (closing) Text(translate('You are ending a session with a device without an organization. Select or create one to attribute this entire session to it.')),
          if (offerAlias) TextField(controller: alias, enabled: !busy, maxLength: api.aliasMaxLength,
            decoration: InputDecoration(labelText: translate('Device alias (optional)'), helperText: translate('For easier navigation. The computer name stays unchanged.'), helperMaxLines: 2)),
          RdgenOrganizationChoices(groups: groups, selected: selected, origin: origin, busy: busy,
            showCreate: false, onChanged: (value) => setState(() { selected = value; })),
          Tooltip(message: translate('Organization creation requires permission from the server'),
            child: TextButton.icon(onPressed: busy || !api.version2 || api.permissions['can_create'] != true ? null : create,
              icon: const Icon(Icons.add), label: Text(translate('Create organization…')))),
          if (busy) const LinearProgressIndicator(),
          if (error != null) Text(error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
          if (error != null) TextButton(onPressed: busy ? null : load, child: Text(translate('Retry'))),
        ])))),
        actions: [
          if (!additional) TextButton(onPressed: mutating ? null : () => finish(RdgenOrganizationDecision.skip),
            child: Text(translate(closing ? 'End without organization' : 'Do not select'))),
          TextButton(onPressed: mutating ? null : () => finish(RdgenOrganizationDecision.cancel),
            child: Text(translate(closing ? 'Return to session' : 'Cancel'))),
          ElevatedButton(onPressed: busy || selected == null || authorizationFailed ||
              (!bound.any((g) => g['id'] == selected) && (!api.version2 || api.permissions['can_attach'] != true)) ? null : submit,
            child: Text(translate(closing ? 'Save and end session' : 'Confirm'))),
        ], onCancel: mutating ? null : () => finish(RdgenOrganizationDecision.cancel));
    });
    return result ?? RdgenOrganizationDecision.cancel;
  } finally { disposed = true; }
}

Future<bool> rdgenConfirmOrganization(OverlayDialogManager manager, String name, {bool reconnecting = false}) async =>
  await manager.show<bool>((setState, close, context) => CustomAlertDialog(
    title: Text(translate(reconnecting ? 'Reconnect to this device for another organization?' : 'Assign this organization to the device?')),
    content: Text('${translate('Selected organization')}: $name\n\n${translate(reconnecting ? 'The current session will end. A new session will be attributed to this organization.' : 'The current session will be attributed to this organization.')}'),
    actions: [TextButton(onPressed: () => close(false), child: Text(translate('Cancel'))),
      ElevatedButton(onPressed: () => close(true), child: Text(translate(reconnecting ? 'Reconnect' : 'Assign organization')))],
    onCancel: () => close(false))) ?? false;

Future<void> rdgenEditDeviceAlias(OverlayDialogManager manager, RdgenOrganizationApi api) async {
  if (!api.canSetAlias || api.alias != '') return;
  final alias = TextEditingController();
  var busy = false;
  var closed = false;
  String? error;
  try {
    await manager.show<void>((setState, close, context) {
      void cancel() { closed = true; close(); }
      Future<void> submit() async {
        if (busy || alias.text.trim().isEmpty) return;
        setState(() { busy = true; error = null; });
        try {
          await api.saveAlias(alias.text);
          if (!closed && context.mounted) { closed = true; close(); }
        } catch (failure) {
          if (!closed && context.mounted) setState(() { error = rdgenOrganizationError(failure); });
        } finally { if (!closed && context.mounted) setState(() { busy = false; }); }
      }
      return CustomAlertDialog(title: Text(translate('Assign device alias')),
        content: _RdgenDialogLifetime(controllers: [alias], child: SizedBox(width: 420, child: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(controller: alias, enabled: !busy, autofocus: true, maxLength: api.aliasMaxLength,
            onChanged: (_) => setState(() {}), decoration: InputDecoration(labelText: translate('Alias'),
              helperText: translate('For easier navigation. The computer name stays unchanged.'), helperMaxLines: 2)),
          if (busy) const LinearProgressIndicator(),
          if (error != null) Text(error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
        ]))), actions: [TextButton(onPressed: busy ? null : cancel, child: Text(translate('Cancel'))),
          ElevatedButton(onPressed: busy || alias.text.trim().isEmpty ? null : submit, child: Text(translate('Save')))],
        onCancel: busy ? null : cancel);
    });
  } finally { closed = true; }
}

// Overlay completion precedes the closing animation; inputs own their controllers until unmount.
class _RdgenDialogLifetime extends StatefulWidget {
  final List<TextEditingController> controllers;
  final Widget child;
  const _RdgenDialogLifetime({required this.controllers, required this.child});
  @override
  State<_RdgenDialogLifetime> createState() => _RdgenDialogLifetimeState();
}
class _RdgenDialogLifetimeState extends State<_RdgenDialogLifetime> {
  @override
  Widget build(BuildContext context) => widget.child;
  @override
  void dispose() { for (final controller in widget.controllers) { controller.dispose(); } super.dispose(); }
}
