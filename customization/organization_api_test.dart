import 'dart:convert';
import 'rdgen_organization_api.dart';
import 'rdgen_session_work_groups.dart';

void check(bool condition) { if (!condition) throw StateError('Organization API contract'); }

Future<void> main() async {
  var creates = 0;
  var attachments = 0;
  final createBodies = <String>[];
  final attachBodies = <String>[];
  final api = RdgenOrganizationApi(Uri.parse('https://console.test/prefix'), '000123',
    (method, uri, body) async {
      check(uri.path.startsWith('/prefix/api/statusdesk/'));
      check(uri.queryParameters['rdgen_request_scope']!.isNotEmpty);
      if (uri.path.endsWith('/organization-options')) return WorkGroupReply(200,
        '{"api_version":2,"total":1,"data":[{"id":7,"name":"A"}],"bindings":[],"permissions":{"can_attach":true,"can_create":true}}');
      check(method == 'POST');
      if (uri.path.endsWith('/organizations')) {
        createBodies.add(body!);
        creates++;
        check(jsonDecode(body)['device_id'] == '000123');
        if (creates == 1) throw StateError('Lost response after durable creation');
        return WorkGroupReply(200, '{"organization":{"id":7,"name":"A"},"user_group_ids":[3]}');
      }
      attachBodies.add(body!);
      attachments++;
      if (attachments == 1) return WorkGroupReply(429, '{}', retryAfter: '120');
      return WorkGroupReply(200, '{"organization":{"id":7,"name":"A"},"bindings":[{"id":7,"name":"A","kind":"primary"}]}');
    });
  try { await api.create({'name':'A'}); throw StateError('Expected denial'); }
  on RdgenOrganizationApiError catch (e) { check(e.status == 403); }
  check(creates == 0);
  check((await api.search()).single['id'] == 7);
  const fields = {'name':'A','note':null,'user_group_ids':[3]};
  try { await api.create(fields); } on StateError { /* Recover the same operation. */ }
  check(api.pendingCreate != null);
  check((await api.create(fields))['id'] == 7);
  check(createBodies.length == 2 && createBodies[0] == createBodies[1]);
  check(RegExp(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')
      .hasMatch(jsonDecode(createBodies.first)['request_id']));
  try { await api.attach(7); } on RdgenOrganizationApiError catch (e) { check(e.status == 429); }
  try { await api.attach(7); } on RdgenOrganizationApiError catch (e) { check(e.status == 429); }
  check(attachments == 1); // Retry-After is honored without resubmitting.
  api.retryAt = DateTime.now().subtract(const Duration(seconds:1));
  await api.attach(7);
  check(attachBodies.length == 2 && attachBodies.first == attachBodies.last);
  check(api.bindings.single['id'] == 7);
  print('Organization permissions, scoped requests, durable retry IDs and rate limiting: OK');
}
