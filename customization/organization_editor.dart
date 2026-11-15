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
      Future<void> submit() async {
        if (busy || name.text.trim().isEmpty) return;
        setState(() { busy = true; error = null; });
        try {
          final ids = selected.toList()..sort();
          final created = await api.create({'name': name.text.trim(),
            'note': note.text.trim().isEmpty ? null : note.text.trim(), 'user_group_ids': ids});
          if (!closed && context.mounted) { closed = true; close(created); }
        } catch (failure) {
          if (failure is RdgenOrganizationApiError && failure.status == 422) api.pendingCreate = null;
          if (!closed && context.mounted) setState(() { error = rdgenOrganizationError(failure); });
        } finally {
          if (!closed && context.mounted) setState(() { busy = false; });
        }
      }
      final locked = busy || api.pendingCreate != null;
      return CustomAlertDialog(title: Text(translate('Create organization…')),
        content: SizedBox(width: 420, child: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, children: [
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
        ]))),
        actions: [TextButton(onPressed: busy ? null : cancel, child: Text(translate('Cancel'))),
          ElevatedButton(onPressed: busy || name.text.trim().isEmpty ? null : submit,
            child: Text(translate(api.pendingCreate == null ? 'Create' : 'Retry')))],
        onCancel: busy ? null : cancel);
    });
  } finally { closed = true; name.dispose(); note.dispose(); }
}

Future<RdgenOrganizationDecision> rdgenEditOrganization({
  required OverlayDialogManager manager, required RdgenOrganizationApi api,
  required List<Map<String, dynamic>> boundChoices,
  required Future<void> Function(int groupId, bool needsAttachment) save,
  Future<List<Map<String, dynamic>>> Function()? loadBound,
  int? origin, bool closing = false, bool additional = false,
}) async {
  final byId = {for (final group in boundChoices) group['id'] as int: group};
  var bound = List<Map<String, dynamic>>.of(boundChoices);
  int? selected = byId.containsKey(origin) ? origin : null;
  var busy = true;
  var mutating = false;
  var authorizationFailed = false;
  var started = false;
  var disposed = false;
  String? error;
  try {
    final result = await manager.show<RdgenOrganizationDecision>((setState, close, context) {
      void finish(RdgenOrganizationDecision decision) { disposed = true; close(decision); }
      Future<void> load() async {
        setState(() { busy = true; });
        try {
          if (loadBound != null) bound = await loadBound();
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
        if (busy || selected == null) return;
        setState(() { busy = true; mutating = true; error = null; });
        try {
          final needsAttachment = !bound.any((g) => g['id'] == selected);
          await save(selected!, needsAttachment);
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
          if (group != null) { created = true; setState(() { byId[group['id'] as int] = group; selected = group['id'] as int; error = null; }); }
        } catch (failure) { if (!disposed && context.mounted) setState(() { error = rdgenOrganizationError(failure); }); }
        finally { if (!disposed && context.mounted) setState(() { busy = false; }); }
        if (created && !disposed && context.mounted) await submit();
      }
      final groups = byId.values.toList()..sort((a,b) => (a['name'] as String).compareTo(b['name'] as String));
      return CustomAlertDialog(title: Text(translate(additional ? 'Add organization' : 'Session organization')),
        content: SizedBox(width: 420, child: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, children: [
          if (closing) Text(translate('You are ending a session with a device without an organization. Select or create one to attribute this entire session to it.')),
          RdgenOrganizationChoices(groups: groups, selected: selected, origin: origin, busy: busy,
            showCreate: false, onChanged: (value) => setState(() { selected = value; })),
          Tooltip(message: translate('Organization creation requires permission from the server'),
            child: TextButton.icon(onPressed: busy || !api.version2 || api.permissions['can_create'] != true ? null : create,
              icon: const Icon(Icons.add), label: Text(translate('Create organization…')))),
          if (busy) const LinearProgressIndicator(),
          if (error != null) Text(error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
          if (error != null) TextButton(onPressed: busy ? null : load, child: Text(translate('Retry'))),
        ]))),
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
