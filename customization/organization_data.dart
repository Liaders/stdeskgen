import 'dart:async';
import 'dart:convert';
import 'package:get/get.dart';
import '../common.dart';
import 'platform_model.dart';
import '../utils/http_service.dart' as http;
import 'rdgen_organization_catalog.dart';
import 'rdgen_session_work_groups.dart';
import 'rdgen_group_refresh.dart';

class RdgenOrganizationData {
  final loading = false.obs;
  final error = ''.obs;
  final _rows = <WorkOrganization>[].obs;
  final _supported = false.obs;
  final _refresh = RdgenGroupRefresh();
  String? _token;
  late final Worker _accountWorker;

  RdgenOrganizationData() {
    _accountWorker = ever(gFFI.userModel.userName, (_) {
      reset();
      unawaited(reload());
    });
    unawaited(reload());
  }

  void reset() {
    _rows.clear();
    _supported.value = false;
    _token = null;
    _refresh.catalogAt = null;
    error.value = '';
  }

  List<WorkOrganization> get groups {
    final rows = _rows.toList();
    if (_supported.value && _token == bind.mainGetLocalOption(key: 'access_token')) return rows;
    final peersByGroup = <String, Set<String>>{};
    for (final peer in gFFI.groupModel.peers) {
      (peersByGroup[peer.device_group_name] ??= <String>{}).add(peer.id);
    }
    return gFFI.groupModel.deviceGroups.map((group) => WorkOrganization(
        null, group.name, peersByGroup[group.name] ?? <String>{})).toList();
  }

  bool _authorized(String token) => gFFI.userModel.isLogin &&
      token == bind.mainGetLocalOption(key: 'access_token');

  List<Map<String, dynamic>>? get cachedGroups =>
      _supported.value && _token == bind.mainGetLocalOption(key: 'access_token')
      ? _rows.map((row) => <String, dynamic>{'id': row.id, 'name': row.name,
          'peer_ids': row.peerIds.toList()}).toList() : null;

  // The caller verifies the enclosing native cache's server and account.
  void restoreCachedGroups(Object? value, String token) {
    if (!_authorized(token) || (_supported.value && _token == token)) return;
    final rows = readWorkOrganizationCache(value);
    if (rows == null) return;
    _token = token;
    _rows.assignAll(rows);
    _supported.value = true;
    // Deliberately leave freshness unset: refresh the snapshot in the background.
  }

  Future<void> reload({bool force = false}) async {
    if (!gFFI.userModel.isLogin) return;
    final token = bind.mainGetLocalOption(key: 'access_token');
    if (token.isEmpty) return;
    final base = Uri.parse(await bind.mainGetApiServer());
    final owner = base.toString() + '\n' + token;
    return _refresh.run(owner, () async {
      if (!force && _refresh.catalogFresh && _token == token) return;
      loading.value = true;
      try {
        final rows = await loadWorkOrganizations(base, token,
          (method, uri, token, body) async {
            final response = await http.get(uri, headers: {'Authorization': 'Bearer $token'});
            if ([401,403].contains(response.statusCode)) reset();
            return WorkGroupReply(response.statusCode, response.body);
          }, () => _authorized(token));
        if (!_authorized(token) || base.toString() != await bind.mainGetApiServer()) return;
        _token = token;
        _rows.assignAll(rows ?? []);
        _supported.value = rows != null;
        _refresh.catalogAt = DateTime.now();
        error.value = '';
      } catch (_) {
        // Keep the last confirmed view for transient network failures.
        if (_authorized(token)) {
          error.value = translate('Failed to load organizations');
        }
      } finally { loading.value = false; }
    }, catalog: force);
  }

  Future<Map<String, dynamic>?> _device(String id, String route) async {
    if (!gFFI.userModel.isLogin) return null;
    final token = bind.mainGetLocalOption(key: 'access_token');
    final base = Uri.parse(await bind.mainGetApiServer());
    await _refresh.settled;
    if (!_authorized(token) || base.toString() != await bind.mainGetApiServer()) return null;
    final uri = base.replace(path: base.path.replaceFirst(RegExp(r'/$'), '') +
      '/api/statusdesk/devices/' + Uri.encodeComponent(id) + '/' + route);
    final response = await http.get(uri, headers: {'Authorization': 'Bearer $token'});
    if (!_authorized(token) || base.toString() != await bind.mainGetApiServer()) return null;
    if (response.statusCode != 200) {
      if ([401,403].contains(response.statusCode)) reset();
      throw StateError('Device refresh failed');
    }
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  Future<void> refreshDevice(String id) async {
    final data = await _device(id, 'work-groups');
    if (data == null) return;
    if (!_supported.value || _token != bind.mainGetLocalOption(key: 'access_token')) {
      await reload(force: true);
      return;
    }
    final bindings = WorkGroupSession.choices(data);
    final byId = {for (final group in bindings) group['id'] as int: group};
    _rows.assignAll(_rows.map((group) {
      final binding = byId[group.id];
      final ids = Set<String>.from(group.peerIds);
      if (binding != null) { ids.add(id); } else { ids.remove(id); }
      return WorkOrganization(group.id, binding?['name'] as String? ?? group.name, ids);
    }).toList());
    for (final group in bindings) {
      if (!_rows.any((row) => row.id == group['id'])) {
        _rows.add(WorkOrganization(group['id'] as int, group['name'] as String, {id}));
      }
    }
    _rows.sort((a,b) => a.name.compareTo(b.name));
    _rows.refresh();
  }

  Future<String?> readAlias(String id) async {
    final data = await _device(id, 'alias');
    return data?['alias'] is String ? data!['alias'] as String : null;
  }

  void dispose() { _accountWorker.dispose(); reset(); }
}
