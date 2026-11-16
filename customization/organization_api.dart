import 'dart:convert';
import 'dart:math';
import 'rdgen_session_work_groups.dart';

class RdgenOrganizationApiError implements Exception {
  final int status;
  RdgenOrganizationApiError(this.status);
}

class RdgenOrganizationMutation {
  final String requestId;
  final Map<String, dynamic> data;
  RdgenOrganizationMutation(Map<String, dynamic> fields)
      : requestId = _uuid(), data = Map.unmodifiable(fields);
  static String _uuid() {
    final random = Random.secure();
    final bytes = List.generate(16, (_) => random.nextInt(256));
    bytes[6] = (bytes[6] & 15) | 64;
    bytes[8] = (bytes[8] & 63) | 128;
    final hex = bytes.map((v) => v.toRadixString(16).padLeft(2, '0')).join();
    return '${hex.substring(0,8)}-${hex.substring(8,12)}-${hex.substring(12,16)}-${hex.substring(16,20)}-${hex.substring(20)}';
  }
  String get body => jsonEncode({...data, 'request_id': requestId});
}

class RdgenOrganizationApi {
  final Uri base;
  final String peerId;
  final Future<WorkGroupReply> Function(String, Uri, String?) request;
  bool version2 = false;
  Map<String, dynamic> permissions = {};
  List<Map<String, dynamic>> bindings = [];
  DateTime? retryAt;
  RdgenOrganizationMutation? pendingCreate;
  RdgenOrganizationMutation? pendingAttach;
  final String _scope = RdgenOrganizationMutation._uuid();
  RdgenOrganizationApi(this.base, this.peerId, this.request);

  Uri uri(String route, [Map<String, String>? query]) => base.replace(
    path: base.path.replaceFirst(RegExp(r'/$'), '') + '/api/statusdesk/$route',
    queryParameters: {...?query, 'rdgen_request_scope': _scope});

  Future<Map<String, dynamic>> _call(String method, Uri uri, [String? body]) async {
    if (method != 'GET' && retryAt != null && DateTime.now().isBefore(retryAt!)) {
      throw RdgenOrganizationApiError(429);
    }
    final reply = await request(method, uri, body);
    if (reply.code == 429) {
      final seconds = int.tryParse(reply.retryAfter ?? '') ?? 60;
      retryAt = DateTime.now().add(Duration(seconds: seconds.clamp(1, 3600).toInt()));
    }
    if (reply.code != 200) throw RdgenOrganizationApiError(reply.code);
    final data = jsonDecode(reply.body);
    if (data is! Map<String, dynamic>) throw FormatException('Invalid organization response');
    return data;
  }

  Future<List<Map<String, dynamic>>> search() async {
    final rows = <Map<String, dynamic>>[];
    for (var page = 1; ; page++) {
      final data = await _call('GET', uri('devices/${Uri.encodeComponent(peerId)}/organization-options',
        {'current': '$page', 'pageSize': '100'}));
      if (data['api_version'] != 2 || data['total'] is! int || data['data'] is! List) {
        throw FormatException('Unsupported organization management API');
      }
      version2 = true;
      permissions = Map<String, dynamic>.from(data['permissions'] as Map);
      bindings = WorkGroupSession.choices({'groups': data['bindings']});
      final current = WorkGroupSession.choices({'groups': data['data']});
      if (current.isEmpty && rows.length < data['total']) throw FormatException('Incomplete organization search');
      rows.addAll(current);
      if (rows.length >= data['total']) return rows;
    }
  }

  Future<Map<String, dynamic>> creationOptions() async {
    if (!version2 || permissions['can_create'] != true) throw RdgenOrganizationApiError(403);
    final data = await _call('GET', uri('organization-create-options', {'device_id': peerId}));
    if (data['api_version'] != 2 || data['can_create'] != true) throw RdgenOrganizationApiError(403);
    return data;
  }

  Future<Map<String, dynamic>> create(Map<String, dynamic> fields) async {
    if (!version2 || permissions['can_create'] != true) throw RdgenOrganizationApiError(403);
    pendingCreate ??= RdgenOrganizationMutation({'device_id': peerId, ...fields});
    final data = await _call('POST', uri('organizations'), pendingCreate!.body);
    final rows = WorkGroupSession.choices({'groups': [data['organization']]});
    if (rows.length != 1) throw FormatException('Invalid created organization');
    pendingCreate = null;
    return rows.single;
  }

  Future<void> attach(int groupId) async {
    if (!version2 || permissions['can_attach'] != true) throw RdgenOrganizationApiError(403);
    if (pendingAttach != null && pendingAttach!.data['group_id'] != groupId) {
      throw RdgenOrganizationApiError(409);
    }
    pendingAttach ??= RdgenOrganizationMutation({'group_id': groupId});
    final Map<String, dynamic> data;
    try {
      data = await _call('POST', uri('devices/${Uri.encodeComponent(peerId)}/work-groups'), pendingAttach!.body);
    } on RdgenOrganizationApiError catch (error) {
      if (error.status == 422) pendingAttach = null;
      rethrow;
    }
    bindings = WorkGroupSession.choices({'groups': data['bindings']});
    pendingAttach = null;
    if (!bindings.any((g) => g['id'] == groupId)) throw RdgenOrganizationApiError(409);
  }
}
