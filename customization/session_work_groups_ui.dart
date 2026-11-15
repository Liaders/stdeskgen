import 'package:flutter/material.dart';
import '../common.dart';
import 'rdgen_session_work_groups.dart';
import 'rdgen_organization_choices.dart';

// This future owns the captured connection even if the transport disconnects.
// A submitted choice may finish saving after disconnect, never on a new session.
Future<void> rdgenChooseWorkGroup(WorkGroupSession session,
    OverlayDialogManager manager, bool Function() canPrompt,
    {required void Function() onDisconnect, bool allowSkip = false,
     bool showUnassigned = false, Future<void> Function()? onSaved}) async {
  try {
    if (!await session.resolve()) return;
    var state = await session.read();
    if (state == null || (state['status'] != 'required' &&
        !(showUnassigned && state['status'] == 'ungrouped'))) return;
    var groups = WorkGroupSession.choices(state);
    if (groups.length == 1) {
      state = await session.select(groups.single['id'] as int);
      if (state == null || state['status'] != 'required') {
        if (onSaved != null) await onSaved();
        return;
      }
      groups = WorkGroupSession.choices(state);
    }
    if (!canPrompt() || !session.authorized()) return;
    int? selected = session.preferredChoice(groups);
    final origin = selected;
    if (origin != null) {
      groups = [...groups.where((g) => g['id'] == origin),
                ...groups.where((g) => g['id'] != origin)];
    }
    var busy = false;
    var closed = false;
    String? error;
    try {
      await manager.show((setState, close, context) {
        void cancel() {
          closed = true;
          close();
          if (!allowSkip) onDisconnect();
        }

        Future<void> submit() async {
          if (busy || selected == null) return;
          setState(() { busy = true; error = null; });
          try {
            final fresh = await session.select(selected!);
            if (closed || !context.mounted) return;
            if (fresh != null && ['selected', 'automatic'].contains(fresh['status'])) {
              if (onSaved != null) await onSaved();
              if (closed || !context.mounted) return;
              closed = true;
              close();
              return;
            }
            setState(() {
              groups = fresh == null ? [] : WorkGroupSession.choices(fresh);
              selected = null;
              error = translate('Organization not selected') + '. ' +
                  translate('Available organizations changed. Please choose again.');
            });
          } catch (_) {
            if (!closed && context.mounted) {
              setState(() { error = translate('Organization not selected') + '. ' +
                  translate('Could not save the organization. Please try again.'); });
            }
          } finally {
            if (!closed && context.mounted) setState(() { busy = false; });
          }
        }

        return CustomAlertDialog(
          title: Row(children: [
            Expanded(child: Text(translate('Session organization'))),
            IconButton(onPressed: busy ? null : cancel,
              tooltip: translate(allowSkip ? 'Close' : 'Disconnect session'), icon: const Icon(Icons.close)),
          ]),
          onCancel: busy ? null : cancel,
          content: SizedBox(width: 360, child: Column(
            mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(translate('Choose an organization for this session.')),
              const SizedBox(height: 12),
              RdgenOrganizationChoices(groups: groups, selected: selected,
                origin: origin, busy: busy,
                onChanged: (value) => setState(() { selected = value; })),
              if (state?['status'] == 'ungrouped')
                Text(translate('Assigning this device requires a server API update')),
              if (busy) const LinearProgressIndicator(),
              if (error != null) Padding(padding: const EdgeInsets.only(top: 8),
                child: Text(error!, style: TextStyle(color: Theme.of(context).colorScheme.error))),
            ])),
          actions: [
            TextButton(onPressed: busy ? null : cancel,
              child: Text(translate(allowSkip ? 'Do not select' : 'Disconnect session'))),
            ElevatedButton(onPressed: busy || selected == null || !session.authorized() ? null : submit,
              child: Text(translate('Confirm'))),
          ],
        );
      }, tag: 'statusdesk-work-group-${session.connectionId}');
    } finally {
      closed = true;
    }
  } catch (_) {
    // Accounting failure must not interrupt the remote connection or invent a choice.
    debugPrint('StatusDesk session organization was not saved or is unavailable');
  }
}
