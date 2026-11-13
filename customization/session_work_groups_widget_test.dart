import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import '../lib/common.dart';
import '../lib/models/rdgen_session_work_groups.dart';
import '../lib/models/rdgen_session_work_groups_ui.dart';
import '../lib/models/rdgen_work_group_origin.dart';

void main() {
  testWidgets('Cancel, single group and save confirmation apply to the captured session', (tester) async {
    late BuildContext context;
    await tester.pumpWidget(MaterialApp(home: Builder(builder: (c) {
      context = c;
      return const Scaffold();
    })));
    var puts = 0;
    var single = false;
    var conflict = false;
    var stale = false;
    int? preferred;
    final saved = Completer<WorkGroupReply>();
    WorkGroupSession session() => WorkGroupSession(
      Uri.parse('https://example.test/api/audit/conn/active'), '123', '18446744073709551615',
      0, 'token', (method, uri, token, body) async {
        if (uri.path.endsWith('/active')) return WorkGroupReply(200, '"guid"');
        if (method == 'PUT') {
          puts++;
          if (single) return WorkGroupReply(200, '{"saved":true}');
          if (conflict) { stale = true; return WorkGroupReply(422, '{}'); }
          return saved.future;
        }
        return WorkGroupReply(200, single
          ? '{"status":"required","groups":[{"id":1,"name":"One"}]}'
          : stale ? '{"status":"required","groups":[{"id":3,"name":"New"}]}'
          : '{"status":"required","groups":[{"id":1,"name":"One"},{"id":2,"name":"Two"}]}');
      }, () => true, preferredGroupId: preferred);
    final manager = OverlayDialogManager(context);
    var disconnects = 0;
    void disconnect() { disconnects++; }
    var flow = rdgenChooseWorkGroup(session(), manager, () => true, onDisconnect: disconnect);
    await tester.pumpAndSettle();
    expect(find.text('Session organization'), findsOneWidget);
    expect(tester.widget<ElevatedButton>(find.byType(ElevatedButton)).onPressed, isNull);
    await tester.tap(find.text('Disconnect session'));
    await tester.pumpAndSettle();
    await flow;
    expect(puts, 0);
    expect(disconnects, 1);

    preferred = 2;
    flow = rdgenChooseWorkGroup(session(), manager, () => true, onDisconnect: disconnect);
    await tester.pumpAndSettle();
    expect(find.text('Selected from the current tab'), findsOneWidget);
    expect(tester.widget<RadioListTile<int>>(find.byType(RadioListTile<int>).first).value, 2);
    expect(tester.widget<RadioListTile<int>>(find.byType(RadioListTile<int>).first).groupValue, 2);
    expect(puts, 0); // Preselection alone never assigns a session.
    await tester.tap(find.text('Two'));
    await tester.pump();
    await tester.tap(find.text('Confirm'));
    await tester.pump(); // A pending PUT is not shown as saved.
    expect(find.text('Session organization'), findsOneWidget);
    expect(find.byType(LinearProgressIndicator), findsOneWidget);
    expect(tester.widget<TextButton>(find.byType(TextButton)).onPressed, isNull);
    saved.complete(WorkGroupReply(200, '{"saved":true}'));
    await tester.pumpAndSettle();
    await flow;
    expect(find.text('Session organization'), findsNothing);
    expect(puts, 1);
    expect(disconnects, 1);

    conflict = true;
    preferred = 99; // An origin removed from the authoritative choices is not selected.
    flow = rdgenChooseWorkGroup(session(), manager, () => true, onDisconnect: disconnect);
    await tester.pumpAndSettle();
    expect(tester.widget<ElevatedButton>(find.byType(ElevatedButton)).onPressed, isNull);
    await tester.tap(find.text('Two'));
    await tester.pump();
    await tester.tap(find.text('Confirm'));
    await tester.pumpAndSettle();
    expect(find.textContaining('Organization not selected'), findsOneWidget);
    expect(tester.widget<ElevatedButton>(find.byType(ElevatedButton)).onPressed, isNull);
    await tester.tap(find.byIcon(Icons.close));
    await tester.pumpAndSettle();
    await flow;
    expect(disconnects, 2);

    // The native CustomAlertDialog Escape handler invokes onCancel.
    stale = false;
    flow = rdgenChooseWorkGroup(session(), manager, () => true, onDisconnect: disconnect);
    await tester.pumpAndSettle();
    tester.widget<CustomAlertDialog>(find.byType(CustomAlertDialog)).onCancel!();
    await tester.pumpAndSettle();
    await flow;
    expect(disconnects, 3);

    conflict = false;
    single = true;
    await rdgenChooseWorkGroup(session(), manager, () => false, onDisconnect: disconnect); // Quick disconnect is not a save veto.
    expect(puts, 3);
    expect(find.text('Session organization'), findsNothing);
  });

  testWidgets('Organization context belongs to one widget and asynchronous launch', (tester) async {
    late BuildContext organizationContext;
    late BuildContext otherContext;
    await tester.pumpWidget(Directionality(textDirection: TextDirection.ltr, child: Column(children: [
      RdgenWorkGroupOrigin(groupId: 7, child: Builder(builder: (c) { organizationContext = c; return const SizedBox(); })),
      Builder(builder: (c) { otherContext = c; return const SizedBox(); }),
    ])));
    expect(RdgenWorkGroupOrigin.read(organizationContext), 7);
    expect(RdgenWorkGroupOrigin.read(otherContext), isNull);
    final launches = await Future.wait([
      runZoned(() async { await Future<void>.value(); return rdgenLaunchingWorkGroup; }, zoneValues: {rdgenWorkGroupZoneKey: 7}),
      runZoned(() async { await Future<void>.value(); return rdgenLaunchingWorkGroup; }, zoneValues: {rdgenWorkGroupZoneKey: 8}),
    ]);
    expect(launches, [7, 8]);
    expect(rdgenLaunchingWorkGroup, isNull);
  });
}
