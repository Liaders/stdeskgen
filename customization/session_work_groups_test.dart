import 'dart:convert';
import 'rdgen_session_work_groups.dart';

void check(bool condition) {
  if (!condition) throw StateError('Session accounting contract violated');
}

Future<void> main() async {
  final calls = <String>[];
  var account = 'operator';
  var conflict = false;
  var pendingAudit = true;
  Future<WorkGroupReply> request(String method, Uri uri, String token, String? body) async {
    check(token == 'operator');
    calls.add('$method $uri ${body ?? ''}');
    if (uri.path.endsWith('/active')) {
      check(uri.queryParameters['conn_type'] == '0');
      if (pendingAudit) { pendingAudit = false; return WorkGroupReply(200, '""'); }
      return WorkGroupReply(200, jsonEncode('guid-${uri.queryParameters['session_id']}'));
    }
    if (method == 'PUT') {
      check(jsonDecode(body!)['group_id'] == 7);
      return WorkGroupReply(conflict ? 409 : 200, conflict ? '{}' : '{"saved":true}');
    }
    return WorkGroupReply(200, conflict
      ? '{"status":"selected","group":{"id":8,"name":"Other session choice"}}'
      : '{"status":"required","group":null,"groups":[{"id":7,"name":"A"},{"id":8,"name":"B"}]}');
  }
  WorkGroupSession make(String id, {WorkGroupRequest? transport}) => WorkGroupSession(
      Uri.parse('https://console.test/prefix/api/audit/conn/active'), '123', id,
      0, 'operator', transport ?? request, () => account == 'operator');

  // Delayed audit; simultaneous connections to the same device, exact u64 strings.
  final first = make('18446744073709551615');
  final second = make('18446744073709551614');
  check(await first.resolve(delay: (_) async {}));
  check(await second.resolve(delay: (_) async {}));
  check((await first.read())!['status'] == 'required');
  check((await second.read())!['status'] == 'required');
  check(!calls.any((c) => c.startsWith('PUT'))); // Cancel means no assignment.
  check((await first.select(7))!['status'] == 'selected');
  check(calls.last.contains('/prefix/api/statusdesk/sessions/guid-18446744073709551615/work-group'));
  check(!calls.last.contains('18446744073709551614'));
  conflict = true;
  final state = await second.select(7);
  check(state!['group']['id'] == 8); // Respect the immutable server snapshot.
  check(calls.last.startsWith('GET '));

  // Account changes cannot submit using captured credentials.
  final count = calls.length;
  account = 'other';
  try { await first.select(7); throw Exception('Expected authorization failure'); }
  on StateError { check(calls.length == count); }
  account = 'operator';
  for (final status in ['automatic', 'selected', 'ungrouped', null]) {
    final s = make('42', transport: (method, uri, token, body) async {
      check(method == 'GET');
      return WorkGroupReply(200, uri.path.endsWith('/active')
          ? '"guid"' : jsonEncode({'status': status, 'group': null}));
    });
    check(await s.resolve());
    check((await s.read())!['status'] == status); // No picker or PUT needed.
  }
  final old = make('43', transport: (_, uri, token, body) async =>
      WorkGroupReply(uri.path.endsWith('/active') ? 200 : 404, '"guid"'));
  check(await old.resolve());
  check(await old.read() == null);
  for (final code in [401, 403, 500, 200]) {
    final failed = make('44', transport: (method, uri, token, body) async =>
        WorkGroupReply(method == 'PUT' ? code : 200,
            method == 'PUT' ? '{"saved":false}' : '"guid"'));
    check(await failed.resolve());
    try { await failed.select(7); throw Exception('Expected save failure'); }
    on StateError { /* No fake saved state. */ }
  }
  print('Exact session IDs, delayed audits, cancellation, conflicts, authorization and unsupported servers: OK');
}
