// Session-scoped accounting only. No device preferences or credential cache.
import 'dart:convert';

class WorkGroupReply {
  final int code;
  final String body;
  WorkGroupReply(this.code, this.body);
}

typedef WorkGroupRequest = Future<WorkGroupReply> Function(
    String method, Uri uri, String token, String? body);

class WorkGroupSession {
  final Uri audit;
  final String peerId, connectionId, token;
  final int connectionType;
  final WorkGroupRequest request;
  final bool Function() authorized;
  final int? preferredGroupId;
  String? _guid;

  WorkGroupSession(this.audit, this.peerId, this.connectionId,
      this.connectionType, this.token, this.request, this.authorized,
      {this.preferredGroupId});

  int? preferredChoice(List<Map<String, dynamic>> groups) =>
      groups.any((g) => g['id'] == preferredGroupId) ? preferredGroupId : null;

  void _check() {
    if (!authorized()) throw StateError('Account changed');
  }

  Future<WorkGroupReply> _request(String method, Uri uri, [String? body]) async {
    _check();
    final reply = await request(method, uri, token, body);
    _check();
    return reply;
  }

  // The u64 remains a decimal STRING, including values above 2^53.
  Future<bool> resolve({Future<void> Function(Duration)? delay}) async {
    if (token.isEmpty || !RegExp(r'^[1-9][0-9]*$').hasMatch(connectionId) ||
        !['https', 'http'].contains(audit.scheme) || audit.userInfo.isNotEmpty ||
        !audit.path.endsWith('/api/audit/conn/active')) return false;
    final uri = audit.replace(queryParameters: {
      'id': peerId, 'session_id': connectionId,
      'conn_type': '$connectionType',
      // The Rust HTTP bridge keys pending responses by URL. Keep this request
      // separate from the independent end-of-session note GUID lookup.
      'statusdesk_work_group': '1',
    });
    const waits = [1, 1, 2, 2, 3, 3];
    for (final seconds in waits) {
      final reply = await _request('GET', uri);
      if (reply.code != 200) return false;
      final guid = jsonDecode(reply.body);
      if (guid is String && guid.isNotEmpty) {
        if (!RegExp(r'^[a-zA-Z0-9-]+$').hasMatch(guid)) return false;
        _guid = guid;
        return true;
      }
      await (delay ?? Future<void>.delayed)(Duration(seconds: seconds));
    }
    return false;
  }

  Uri get _uri => audit.replace(
      path: audit.path.substring(0, audit.path.length - '/audit/conn/active'.length) +
          '/statusdesk/sessions/$_guid/work-group', query: '', fragment: '');

  Future<Map<String, dynamic>?> read() async {
    if (_guid == null) throw StateError('Session not resolved');
    final reply = await _request('GET', _uri);
    if ([404, 405, 501].contains(reply.code)) return null; // Older servers.
    if (reply.code != 200) throw StateError('Work group read: ${reply.code}');
    final state = jsonDecode(reply.body);
    if (state is! Map<String, dynamic> ||
        ![null, 'required', 'automatic', 'selected', 'ungrouped'].contains(state['status'])) {
      throw FormatException('Invalid work group state');
    }
    return state;
  }

  Future<Map<String, dynamic>?> select(int groupId) async {
    final reply = await _request('PUT', _uri, jsonEncode({'group_id': groupId}));
    if (reply.code == 200 && jsonDecode(reply.body) is Map &&
        jsonDecode(reply.body)['saved'] == true) {
      return {'status': 'selected', 'group': {'id': groupId}};
    }
    // Never overwrite a concurrent choice; re-read the server snapshot.
    if (reply.code == 409 || reply.code == 422) return read();
    throw StateError('Work group not saved: ${reply.code}');
  }

  static List<Map<String, dynamic>> choices(Map<String, dynamic> state) {
    final groups = state['groups'];
    if (groups is! List) return [];
    return groups.whereType<Map<String, dynamic>>().where((g) =>
        g['id'] is int && g['id'] > 0 && g['name'] is String).toList();
  }
}
