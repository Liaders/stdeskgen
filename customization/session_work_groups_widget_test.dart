import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import '../lib/common.dart';
import '../lib/models/rdgen_session_work_groups.dart';
import '../lib/models/rdgen_session_work_groups_ui.dart';

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
      }, () => true);
    final manager = OverlayDialogManager(context);
    var flow = rdgenChooseWorkGroup(session(), manager, () => true);
    await tester.pumpAndSettle();
    expect(find.text('Session organization'), findsOneWidget);
    expect(tester.widget<ElevatedButton>(find.byType(ElevatedButton)).onPressed, isNull);
    await tester.tap(find.text('Cancel'));
    await tester.pumpAndSettle();
    await flow;
    expect(puts, 0);

    flow = rdgenChooseWorkGroup(session(), manager, () => true);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Two'));
    await tester.pump();
    await tester.tap(find.text('Save'));
    await tester.pump(); // A pending PUT is not shown as saved.
    expect(find.text('Session organization'), findsOneWidget);
    expect(find.byType(LinearProgressIndicator), findsOneWidget);
    saved.complete(WorkGroupReply(200, '{"saved":true}'));
    await tester.pumpAndSettle();
    await flow;
    expect(find.text('Session organization'), findsNothing);
    expect(puts, 1);

    conflict = true;
    flow = rdgenChooseWorkGroup(session(), manager, () => true);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Two'));
    await tester.pump();
    await tester.tap(find.text('Save'));
    await tester.pumpAndSettle();
    expect(find.textContaining('Organization not selected'), findsOneWidget);
    expect(tester.widget<ElevatedButton>(find.byType(ElevatedButton)).onPressed, isNull);
    await tester.tap(find.text('Cancel'));
    await tester.pumpAndSettle();
    await flow;

    conflict = false;
    single = true;
    await rdgenChooseWorkGroup(session(), manager, () => false); // Quick disconnect is not a save veto.
    expect(puts, 3);
    expect(find.text('Session organization'), findsNothing);
  });
}
