import 'dart:async';
import 'package:get/get.dart';
import '../common.dart';
import 'platform_model.dart';
import '../utils/http_service.dart' as http;
import 'rdgen_organization_catalog.dart';
import 'rdgen_session_work_groups.dart';

class RdgenOrganizationData {
  final loading = false.obs;
  final error = ''.obs;
  final _rows = <WorkOrganization>[].obs;
  final _supported = false.obs;
  String? _token;
  bool _disposed = false;
  late final Worker _pullWorker;
  late final Worker _accountWorker;

  RdgenOrganizationData() {
    _pullWorker = ever(gFFI.groupModel.groupLoading, (bool busy) {
      if (!busy) unawaited(reload());
    });
    _accountWorker = ever(gFFI.userModel.userName, (_) {
      _rows.clear();
      _supported.value = false;
      _token = null;
      unawaited(reload());
    });
    unawaited(reload());
  }

  List<WorkOrganization> get groups {
    final rows = _rows.toList();
    if (_supported.value && _token == bind.mainGetLocalOption(key: 'access_token')) return rows;
    // Older servers: the existing primary-group view, without inferred IDs.
    return gFFI.groupModel.deviceGroups.map((group) => WorkOrganization(null, group.name,
        gFFI.groupModel.peers.where((peer) => peer.device_group_name == group.name)
            .map((peer) => peer.id).toSet())).toList();
  }

  Future<void> reload() async {
    if (_disposed || loading.value || !gFFI.userModel.isLogin) return;
    final token = bind.mainGetLocalOption(key: 'access_token');
    if (token.isEmpty) return;
    loading.value = true;
    bool authorized() => !_disposed && gFFI.userModel.isLogin &&
        token == bind.mainGetLocalOption(key: 'access_token');
    try {
      final base = Uri.parse(await bind.mainGetApiServer());
      final rows = await loadWorkOrganizations(base, token,
        (method, uri, token, body) async {
          final response = await http.get(uri, headers: {'Authorization': 'Bearer $token'});
          return WorkGroupReply(response.statusCode, response.body);
        }, authorized);
      if (!authorized()) return;
      _token = token;
      _rows.assignAll(rows ?? []);
      _supported.value = rows != null;
      error.value = '';
    } catch (_) {
      if (authorized()) {
        _rows.clear();
        // A failed supported API is not treated as an older server.
        _token = token;
        _supported.value = true;
        error.value = translate('Failed to load organizations');
      }
    } finally {
      loading.value = false;
      if (!_disposed && gFFI.userModel.isLogin &&
          token != bind.mainGetLocalOption(key: 'access_token')) unawaited(reload());
    }
  }

  void dispose() {
    _disposed = true;
    _pullWorker.dispose();
    _accountWorker.dispose();
    _rows.clear();
    _token = null;
  }
}
