import 'dart:convert';
import '../common.dart';
import 'platform_model.dart';
import 'rdgen_session_work_groups.dart';
import 'rdgen_organization_api.dart';
import 'rdgen_device_refresh.dart';

/// Each engine shares the native local-option store, never credentials or bindings.
RdgenOrganizationApi rdgenStoredOrganizationApi(Uri base, String peer,
    Future<WorkGroupReply> Function(String, Uri, String?) request) {
  String account() {
    try {
      final data = jsonDecode(bind.mainGetLocalOption(key: 'user_info'));
      return (data['id'] ?? data['name'] ?? '').toString();
    } catch (_) { return ''; }
  }
  final owner = account();
  final key = 'rdgen-org-options-v1-' + base64Url.encode(utf8.encode(jsonEncode([base.toString(), owner, peer])));
  return RdgenOrganizationApi(base, peer, request,
    onDeviceChanged: () async {
      if (owner.isNotEmpty && account() == owner) await rdgenNotifyDeviceChanged(base, peer);
    },
    readCatalog: () => owner.isNotEmpty && account() == owner ? bind.mainGetLocalOption(key: key) : '',
    writeCatalog: (value) async {
      if (owner.isNotEmpty && account() == owner) await bind.mainSetLocalOption(key: key, value: value);
    });
}
