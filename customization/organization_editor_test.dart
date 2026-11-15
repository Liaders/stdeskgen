import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import '../lib/common.dart';
import '../lib/models/rdgen_session_organization.dart';
import '../lib/models/rdgen_session_work_groups.dart';

void main() {
  testWidgets('Close reminder waits for exact-session persistence; extra binding keeps the saved organization', (tester) async {
    late BuildContext context;
    await tester.pumpWidget(MaterialApp(home: Builder(builder: (c) { context = c; return const Scaffold(); })));
    final manager = OverlayDialogManager(context);
    final controller = RdgenSessionOrganization();
    final confirm = Completer<WorkGroupReply>();
    var saved = false;
    var extra = false;
    var puts = 0;
    var posts = 0;
    final session = WorkGroupSession(Uri.parse('https://console.test/api/audit/conn/active'),
      '000123', '18446744073709551615', 0, 'token', (method, uri, token, body) async {
        if (uri.path.endsWith('/active')) {
          expect(uri.queryParameters['session_id'], '18446744073709551615');
          return WorkGroupReply(200, '"exact-guid"');
        }
        if (uri.path.endsWith('/organization-options')) return WorkGroupReply(200, jsonEncode({
          'api_version':2, 'total':2, 'data':[{'id':7,'name':'A'},{'id':8,'name':'B'}],
          'bindings': saved ? [{'id':7,'name':'A'}] : [],
          'permissions':{'can_attach':true,'can_create':false},
        }));
        if (method == 'POST') {
          posts++;
          expect(uri.path, '/api/statusdesk/devices/000123/work-groups');
          expect(jsonDecode(body!)['group_id'], 8);
          extra = true;
          return WorkGroupReply(200, '{"organization":{"id":8,"name":"B"},"bindings":[{"id":7,"name":"A"},{"id":8,"name":"B"}]}');
        }
        expect(uri.path, '/api/statusdesk/sessions/exact-guid/work-group');
        if (method == 'PUT') {
          puts++;
          expect(jsonDecode(body!)['attach_device_if_needed'], true);
          final response = await confirm.future;
          saved = true;
          return response;
        }
        return WorkGroupReply(200, jsonEncode({
          'api_version':2, 'device_has_organization':saved,
          'permissions':{'can_attach':true,'can_create':false,'can_assign':!saved,'can_attach_and_assign':!saved},
          'bindings':saved ? [{'id':7,'name':'A'}, if (extra) {'id':8,'name':'B'}] : [],
          'status':saved ? 'selected':'ungrouped',
          'group':saved ? {'id':7,'name':'Recorded A'} : null, 'groups':[],
        }));
      }, () => true);
    await controller.attach(session, manager, () => true, preflightDone: true);
    expect(controller.needsReminder, true);
    var ending = controller.beforeClose(manager);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Return to session'));
    await tester.pumpAndSettle();
    expect(await ending, true);
    expect(puts, 0);
    ending = controller.beforeClose(manager);
    await tester.pumpAndSettle();
    await tester.tap(find.text('A'));
    await tester.pump();
    await tester.tap(find.text('Save and end session'));
    await tester.pump();
    expect(controller.assigned, false);
    expect(find.byType(LinearProgressIndicator), findsOneWidget);
    confirm.complete(WorkGroupReply(200, '{"saved":true}'));
    await tester.pumpAndSettle();
    expect(await ending, false);
    expect(controller.name, 'Recorded A');
    expect(puts, 1);
    expect(await controller.beforeClose(manager), false);

    final adding = controller.choose(manager, () => true);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Add organization'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('B'));
    await tester.pump();
    await tester.tap(find.text('Confirm'));
    await tester.pumpAndSettle();
    await adding;
    expect(posts, 1);
    expect(puts, 1);
    expect(controller.name, 'Recorded A');
    expect(controller.additionalCount, 1);
  });
}
