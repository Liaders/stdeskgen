import 'package:flutter/material.dart';
import '../common.dart';
import 'rdgen_session_work_groups.dart';

// This future owns the captured connection even if the transport disconnects.
// A submitted choice may finish saving after disconnect, never on a new session.
Future<void> rdgenChooseWorkGroup(WorkGroupSession session,
    OverlayDialogManager manager, bool Function() canPrompt) async {
  try {
    if (!await session.resolve()) return;
    var state = await session.read();
    if (state == null || state['status'] != 'required') return;
    var groups = WorkGroupSession.choices(state);
    if (groups.length == 1) {
      state = await session.select(groups.single['id'] as int);
      if (state == null || state['status'] != 'required') return;
      groups = WorkGroupSession.choices(state);
    }
    if (!canPrompt() || !session.authorized()) return;
    int? selected;
    var busy = false;
    var closed = false;
    String? error;
    try {
      await manager.show((setState, close, context) {
        void cancel() {
          closed = true;
          close();
        }

        Future<void> submit() async {
          if (busy || selected == null) return;
          setState(() { busy = true; error = null; });
          try {
            final fresh = await session.select(selected!);
            if (closed || !context.mounted) return;
            if (fresh != null && ['selected', 'automatic'].contains(fresh['status'])) {
              cancel();
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
          title: Text(translate('Session organization')),
          onCancel: cancel,
          content: SizedBox(width: 360, child: Column(
            mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(translate('Choose an organization for this session.')),
              const SizedBox(height: 12),
              ConstrainedBox(constraints: const BoxConstraints(maxHeight: 300),
                child: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min,
                  children: groups.map((g) => RadioListTile<int>(
                    value: g['id'] as int, groupValue: selected,
                    title: Text(g['name'] as String), dense: true,
                    onChanged: busy ? null : (value) => setState(() { selected = value; }),
                  )).toList()))),
              if (busy) const LinearProgressIndicator(),
              if (error != null) Padding(padding: const EdgeInsets.only(top: 8),
                child: Text(error!, style: TextStyle(color: Theme.of(context).colorScheme.error))),
            ])),
          actions: [
            TextButton(onPressed: cancel, child: Text(translate('Cancel'))),
            ElevatedButton(onPressed: busy || selected == null || !session.authorized() ? null : submit,
              child: Text(translate('Save'))),
          ],
        );
      }, tag: 'statusdesk-work-group-${session.connectionId}', backDismiss: true);
    } finally {
      closed = true;
    }
  } catch (_) {
    // Accounting failure must not interrupt the remote connection or invent a choice.
    debugPrint('StatusDesk session organization was not saved or is unavailable');
  }
}
