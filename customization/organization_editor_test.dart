import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import '../lib/common.dart';
import '../lib/models/rdgen_session_organization.dart';
import '../lib/models/rdgen_session_work_groups.dart';
import '../lib/models/rdgen_organization_api.dart';
import '../lib/models/rdgen_organization_editor.dart';

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
    final secondary = RdgenSessionOrganization();
    await secondary.attach(WorkGroupSession(session.audit, session.peerId,
        session.connectionId, session.connectionType, session.token, session.request,
        session.authorized), manager, () => true, preflightDone: true);
    expect(controller.needsReminder, true);
    var ending = controller.beforeClose(manager);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Return to session'));
    await tester.pumpAndSettle();
    expect(await ending, true);
    expect(puts, 0);
    ending = controller.beforeClose(manager);
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField).last, 'A');
    await tester.pumpAndSettle();
    await tester.tap(find.byWidgetPredicate((w) => w is Text && w.data == 'A'));
    await tester.pump();
    await tester.tap(find.text('Save and end session'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(ElevatedButton, 'Assign organization'));
    await tester.pump();
    expect(controller.assigned, false);
    expect(find.byType(LinearProgressIndicator), findsOneWidget);
    confirm.complete(WorkGroupReply(200, '{"saved":true}'));
    await tester.pumpAndSettle();
    expect(await ending, false);
    expect(controller.name, 'Recorded A');
    expect(puts, 1);
    expect(await controller.beforeClose(manager), false);
    // A different display window may still hold the pre-assignment snapshot.
    final staleClosing = secondary.beforeClose(manager);
    await tester.pumpAndSettle();
    expect(await staleClosing, false);
    expect(secondary.name, 'Recorded A');
    expect(puts, 1);

    final reopened = <int>[];
    final adding = controller.choose(manager, () => true, restart: (id) async { reopened.add(id); });
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField).last, 'B');
    await tester.pumpAndSettle();
    await tester.tap(find.byWidgetPredicate((w) => w is Text && w.data == 'B'));
    await tester.pump();
    await tester.tap(find.text('Confirm'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Reconnect'));
    await tester.pumpAndSettle();
    await adding;
    expect(reopened, [8]);
    expect(posts, 1);
    expect(puts, 1);
    expect(controller.name, 'Recorded A');
    expect(controller.additionalCount, 1);
  });
  testWidgets('Bound selection skips attachment; new binding confirms; alias edit prefills', (tester) async {
    late BuildContext context;
    await tester.pumpWidget(MaterialApp(home: Builder(builder: (c) { context = c; return const Scaffold(); })));
    final manager = OverlayDialogManager(context);
    var assignments = 0;
    var attaches = 0;
    final api = RdgenOrganizationApi(Uri.parse('https://console.test'), '000123', (method, uri, body) async {
      if (uri.path.endsWith('/alias')) {
        expect(method, 'PUT');
        expect(jsonDecode(body!)['alias'], 'New alias');
        return WorkGroupReply(200, '{"api_version":2,"device_id":"000123","alias":"New alias","can_set_alias":true,"max_length":255,"saved":true}');
      }
      return WorkGroupReply(200, '{"api_version":2,"total":2,"data":[{"id":7,"name":"Bound"},{"id":8,"name":"New"}],"bindings":[{"id":7,"name":"Bound"}],"permissions":{"can_attach":true,"can_create":true}}');
    })..canSetAlias = true..alias = 'Existing alias';
    Future<RdgenOrganizationDecision> edit() => rdgenEditOrganization(manager: manager, api: api,
      boundChoices: [{'id':7,'name':'Bound'}], origin: 7,
      save: (id, attach) async { assignments++; if (attach) attaches++; });
    var editing = edit();
    await tester.pumpAndSettle();
    expect(find.text('Choose organization'), findsOneWidget);
    expect(find.text('New'), findsNothing);
    expect(find.text('Create organization…'), findsNothing);
    expect(tester.widget<RadioListTile<int>>(find.byType(RadioListTile<int>)).groupValue, 7);
    await tester.tap(find.text('Confirm'));
    await tester.pumpAndSettle();
    expect(await editing, RdgenOrganizationDecision.saved);
    expect(assignments, 1);
    expect(attaches, 0);
    editing = edit();
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField).last, 'New');
    await tester.pumpAndSettle();
    await tester.tap(find.byWidgetPredicate((w) => w is Text && w.data == 'New'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Confirm'));
    await tester.pumpAndSettle();
    expect(assignments, 1);
    await tester.tap(find.text('Cancel').last);
    await tester.pumpAndSettle();
    expect(attaches, 0);
    await tester.tap(find.text('Confirm'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(ElevatedButton, 'Assign organization'));
    await tester.pumpAndSettle();
    expect(await editing, RdgenOrganizationDecision.saved);
    expect(attaches, 1);
    final alias = rdgenEditDeviceAlias(manager, api);
    await tester.pumpAndSettle();
    expect(find.text('Existing alias'), findsOneWidget);
    await tester.enterText(find.byType(TextField), 'New alias');
    await tester.tap(find.text('Save'));
    await tester.pumpAndSettle();
    await alias;
    expect(api.alias, 'New alias');
  });
}
