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

Future<RdgenOrganizationDecision> rdgenEditOrganization({
  required OverlayDialogManager manager, required RdgenOrganizationApi api,
  required List<Map<String, dynamic>> boundChoices,
  required Future<void> Function(int groupId, bool needsAttachment) save,
  Future<List<Map<String, dynamic>>> Function()? loadBound,
  bool Function()? assignmentConfirmed,
  int? origin, int? currentGroup, bool closing = false, bool additional = false, bool reconnecting = false,
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
  final alias = TextEditingController(text: api.alias ?? '');
  final offerAlias = api.canSetAlias;
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
          if (api.version2) bound = List<Map<String, dynamic>>.of(api.bindings);
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
        final needsAttachment = !bound.any((g) => g['id'] == selectedId);
        final willReconnect = reconnecting && selectedId != currentGroup;
        final confirmed = (!needsAttachment && !willReconnect) || await rdgenConfirmOrganization(manager, selectedName, reconnecting: willReconnect, attaching: needsAttachment);
        confirming = false;
        if (!confirmed || disposed || !context.mounted) return;
        setState(() { busy = true; mutating = true; error = null; });
        try {
          if (offerAlias && api.alias != alias.text.trim()) await api.saveAlias(alias.text);
          await save(selectedId, needsAttachment);
          if (!disposed && context.mounted) finish(RdgenOrganizationDecision.saved);
        } catch (failure) {
          if (!disposed && context.mounted) setState(() { error = rdgenOrganizationError(failure); });
          if (failure is RdgenOrganizationApiError && [409,422].contains(failure.status)) await load();
        } finally { if (!disposed && context.mounted) setState(() { busy = false; mutating = false; }); }
      }
      Future<void> saveAlias() async {
        if (busy || !offerAlias) return;
        setState(() { busy = true; mutating = true; error = null; });
        try {
          await api.saveAlias(alias.text);
          if (!disposed && context.mounted) showToast(translate('Saved'));
        } catch (failure) {
          if (!disposed && context.mounted) setState(() { error = rdgenOrganizationError(failure); });
        } finally {
          if (!disposed && context.mounted) setState(() { busy = false; mutating = false; });
        }
      }
      final groups = byId.values.toList()..sort((a,b) => (a['name'] as String).compareTo(b['name'] as String));
      return CustomAlertDialog(title: Text(translate('Choose organization')),
        content: _RdgenDialogLifetime(controllers: [alias], child: SizedBox(width: 420, child: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, children: [
          if (closing) Text(translate('You are ending a session with a device without an organization. Select one to attribute this entire session to it.')),
          if (offerAlias) TextField(controller: alias, enabled: !busy, maxLength: api.aliasMaxLength,
            decoration: InputDecoration(labelText: translate('Device alias (optional)'),
              suffixIcon: IconButton(onPressed: busy ? null : saveAlias, tooltip: translate('Save device alias'), icon: const Icon(Icons.check)), helperText: translate('For easier navigation. The computer name stays unchanged.'), helperMaxLines: 2)),
          RdgenOrganizationChoices(groups: groups, boundGroups: bound, selected: selected, origin: origin, busy: busy,
            showCreate: false, onChanged: (value) => setState(() { selected = value; })),
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

Future<bool> rdgenConfirmOrganization(OverlayDialogManager manager, String name, {bool reconnecting = false, bool attaching = false}) async =>
  await manager.show<bool>((setState, close, context) => CustomAlertDialog(
    title: Text(translate(reconnecting ? 'Reconnect to this device for another organization?' : 'Assign this organization to the device?')),
    content: Text('${translate('Selected organization')}: $name\n\n${translate(reconnecting && attaching ? 'The organization will be assigned to the device. The current session will end and a new session will begin.' : reconnecting ? 'The current session will end. A new session will be attributed to this organization.' : 'The current session will be attributed to this organization.')}'),
    actions: [TextButton(onPressed: () => close(false), child: Text(translate('Cancel'))),
      ElevatedButton(onPressed: () => close(true), child: Text(translate(reconnecting ? 'Reconnect' : 'Assign organization')))],
    onCancel: () => close(false))) ?? false;

Future<void> rdgenEditDeviceAlias(OverlayDialogManager manager, RdgenOrganizationApi api) async {
  if (!api.canSetAlias) return;
  final alias = TextEditingController(text: api.alias ?? '');
  var busy = false;
  var closed = false;
  String? error;
  try {
    await manager.show<void>((setState, close, context) {
      void cancel() { closed = true; close(); }
      Future<void> submit() async {
        if (busy) return;
        setState(() { busy = true; error = null; });
        try {
          await api.saveAlias(alias.text);
          if (!closed && context.mounted) { closed = true; close(); }
        } catch (failure) {
          if (!closed && context.mounted) setState(() { error = rdgenOrganizationError(failure); });
        } finally { if (!closed && context.mounted) setState(() { busy = false; }); }
      }
      return CustomAlertDialog(title: Text(translate('Edit device alias')),
        content: _RdgenDialogLifetime(controllers: [alias], child: SizedBox(width: 420, child: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(controller: alias, enabled: !busy, autofocus: true, maxLength: api.aliasMaxLength,
            onChanged: (_) => setState(() {}), decoration: InputDecoration(labelText: translate('Alias'),
              helperText: translate('For easier navigation. The computer name stays unchanged.'), helperMaxLines: 2)),
          if (busy) const LinearProgressIndicator(),
          if (error != null) Text(error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
        ]))), actions: [TextButton(onPressed: busy ? null : cancel, child: Text(translate('Cancel'))),
          ElevatedButton(onPressed: busy ? null : submit, child: Text(translate('Save')))],
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
