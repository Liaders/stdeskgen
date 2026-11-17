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
  await aliasContract();
  await catalogCacheContract();
  print('Organization permissions, scoped requests, durable retry IDs and rate limiting: OK');
}

Future<void> aliasContract() async {
  var alias = '';
  var fail = true;
  final api = RdgenOrganizationApi(Uri.parse('https://console.test'), '000123', (method, uri, body) async {
    check(uri.path == '/api/statusdesk/devices/000123/alias');
    if (method == 'PUT') {
      alias = jsonDecode(body!)['alias'];
      if (fail) { fail = false; throw StateError('Lost alias response'); }
    }
    return WorkGroupReply(200, jsonEncode({'api_version':2,'device_id':'000123',
      'alias':alias,'can_set_alias':true,'max_length':255, if (method == 'PUT') 'saved':true}));
  });
  await api.readAlias();
  check(api.canSetAlias && api.alias == '');
  var failed = false;
  try { await api.saveAlias('New name'); } catch (_) { failed = true; }
  check(failed && api.alias == 'New name'); // Recovery reads the authoritative value.
  await api.saveAlias('0');
  check(api.alias == '0');
  final old = RdgenOrganizationApi(api.base, api.peerId, (_, __, ___) async => WorkGroupReply(404, '{}'));
  await old.readAlias();
  check(!old.canSetAlias && old.alias == null);
}

Future<void> catalogCacheContract() async {
  var stored = '';
  var pages = 0;
  var bound = 1;
  var forbidden = false;
  RdgenOrganizationApi api() => RdgenOrganizationApi(Uri.parse('https://console.test'), '123', (method, uri, body) async {
    if (forbidden) return WorkGroupReply(403, '{}');
    pages++;
    final page = int.parse(uri.queryParameters['current']!);
    return WorkGroupReply(200, jsonEncode({'api_version':2,'total':101,
      'data': List.generate(page == 1 ? 100 : 1, (i) => {'id':(page - 1)*100+i+1,'name':'Group ' + ((page - 1)*100+i+1).toString()}),
      'bindings':[{'id':bound,'name':'Group ' + bound.toString()}], 'permissions':{'can_attach':true}}));
  }, readCatalog: () => stored, writeCatalog: (value) async { stored = value; });
  check((await api().search()).length == 101 && pages == 2);
  bound = 2;
  final fresh = api();
  check((await fresh.search()).length == 101 && pages == 3);
  check(fresh.bindings.single['id'] == 2);
  final expired = jsonDecode(stored);
  expired['saved_at'] = DateTime.now().subtract(const Duration(hours:13)).toIso8601String();
  stored = jsonEncode(expired);
  await api().search();
  check(pages == 5);
  forbidden = true;
  try { await api().search(); } on RdgenOrganizationApiError catch (e) { check(e.status == 403); }
  check(stored.isEmpty);
}
