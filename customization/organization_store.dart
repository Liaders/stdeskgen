import 'dart:convert';
import 'package:flutter/foundation.dart' show debugPrint;
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
  late final RdgenOrganizationApi api;
  api = RdgenOrganizationApi(base, peer, request,
    onDeviceChanged: () async {
      if (owner.isNotEmpty && account() == owner) {
        if (api.alias != null) try {
          final token = bind.mainGetLocalOption(key: 'access_token');
          Map<String, dynamic> titles = {};
          try { titles = Map<String, dynamic>.from(jsonDecode(bind.mainGetLocalOption(key: 'rdgen-session-title-peers-v1'))); } catch (_) {}
          if (token.isNotEmpty) {
            final peers = titles['access_token'] == token && titles['peers'] is Map
              ? Map<String, dynamic>.from(titles['peers']) : <String, dynamic>{};
            final previous = peers[peer] is Map ? Map<String, dynamic>.from(peers[peer]) : <String, dynamic>{};
            peers[peer] = {...previous, 'alias': api.alias};
            await bind.mainSetLocalOption(key: 'rdgen-session-title-peers-v1', value: jsonEncode({'access_token': token, 'peers': peers}));
          }
        } catch (_) { debugPrint('Server alias saved; local name cache refresh unavailable'); }
        await rdgenNotifyDeviceChanged(base, peer);
      }
    },
    readCatalog: () => owner.isNotEmpty && account() == owner ? bind.mainGetLocalOption(key: key) : '',
    writeCatalog: (value) async {
      if (owner.isNotEmpty && account() == owner) await bind.mainSetLocalOption(key: key, value: value);
    });
  return api;
}
