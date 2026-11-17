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
  String? alias;
  bool canSetAlias = false;
  int aliasMaxLength = 255;
  RdgenOrganizationMutation? pendingCreate;
  RdgenOrganizationMutation? pendingAttach;
  final String _scope = RdgenOrganizationMutation._uuid();
  final Future<void> Function()? onDeviceChanged;
  final String Function()? readCatalog;
  final Future<void> Function(String)? writeCatalog;
  RdgenOrganizationApi(this.base, this.peerId, this.request, {this.readCatalog, this.writeCatalog, this.onDeviceChanged});

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
    if ([401, 403, 409, 422].contains(reply.code)) await writeCatalog?.call('');
    if (reply.code != 200) throw RdgenOrganizationApiError(reply.code);
    final data = jsonDecode(reply.body);
    if (data is! Map<String, dynamic>) throw FormatException('Invalid organization response');
    return data;
  }

  Map<String, dynamic>? _cachedCatalog() {
    try {
      final raw = readCatalog?.call() ?? '';
      return raw.isEmpty ? null : jsonDecode(raw) as Map<String, dynamic>;
    } catch (_) { return null; }
  }

  // Cached names are a search preview, never permission or binding evidence.
  List<Map<String, dynamic>> cachedChoices() {
    final cached = _cachedCatalog();
    final saved = DateTime.tryParse(cached?['saved_at'] is String ? cached!['saved_at'] as String : '');
    if (saved == null) return [];
    final age = DateTime.now().difference(saved);
    if (age.isNegative || age >= const Duration(hours: 12)) return [];
    return WorkGroupSession.choices({'groups': cached?['rows'] ?? []});
  }

  Future<List<Map<String, dynamic>>> search() async {
    final cached = _cachedCatalog();
    final rows = <Map<String, dynamic>>[];
    for (var page = 1; ; page++) {
      final data = await _call('GET', uri('devices/${Uri.encodeComponent(peerId)}/organization-options',
        {'current': '$page', 'pageSize': '500'}));
      if (data['api_version'] != 2 || data['total'] is! int || data['data'] is! List) {
        throw FormatException('Unsupported organization management API');
      }
      version2 = true;
      permissions = Map<String, dynamic>.from(data['permissions'] as Map);
      bindings = WorkGroupSession.choices({'groups': data['bindings']});
      final current = WorkGroupSession.choices({'groups': data['data']});
      if (page == 1 && cached != null) {
        final savedAt = DateTime.tryParse(cached['saved_at'] is String ? cached['saved_at'] as String : '');
        final age = savedAt == null ? null : DateTime.now().difference(savedAt);
        final savedRows = WorkGroupSession.choices({'groups': cached['rows'] ?? []});
        if (age != null && !age.isNegative && age < const Duration(hours: 12) &&
            savedRows.length == data['total'] &&
            jsonEncode(cached['permissions']) == jsonEncode(permissions) &&
            jsonEncode(savedRows.take(current.length).toList()) == jsonEncode(current)) {
          return savedRows; // Bindings and permissions above are always from today's server reply.
        }
      }
      if (current.isEmpty && rows.length < data['total']) throw FormatException('Incomplete organization search');
      rows.addAll(current);
      if (rows.length >= data['total']) {
        await writeCatalog?.call(jsonEncode({'saved_at': DateTime.now().toUtc().toIso8601String(),
          'rows': rows, 'permissions': permissions}));
        return rows;
      }
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

  Uri get _aliasUri => uri('devices/${Uri.encodeComponent(peerId)}/alias');
  void _acceptAlias(Map<String, dynamic> data) {
    if (data['api_version'] != 2 || data['device_id'] != peerId || data['alias'] is! String ||
        data['can_set_alias'] is! bool || data['max_length'] is! int || data['max_length'] < 1) {
      throw FormatException('Invalid device alias response');
    }
    alias = data['alias'] as String;
    canSetAlias = data['can_set_alias'] == true;
    aliasMaxLength = data['max_length'] as int;
  }
  Future<void> readAlias() async {
    canSetAlias = false;
    try { _acceptAlias(await _call('GET', _aliasUri)); }
    on RdgenOrganizationApiError catch (error) {
      if (![404,405,501].contains(error.status)) rethrow;
    }
  }
  Future<void> saveAlias(String value) async {
    if (!canSetAlias) throw RdgenOrganizationApiError(403);
    try {
      final data = await _call('PUT', _aliasUri, jsonEncode({'alias': value.trim()}));
      if (data['saved'] != true) throw FormatException('Alias save not confirmed');
      _acceptAlias(data);
      await onDeviceChanged?.call();
    } catch (_) {
      // Refresh before another explicit retry; never claim an uncertain write succeeded.
      try { await readAlias(); } catch (_) {}
      rethrow;
    }
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
    await onDeviceChanged?.call();
  }
}
