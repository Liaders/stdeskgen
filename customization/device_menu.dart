import 'dart:convert';
import 'dart:async';
import 'package:flutter/widgets.dart';
import '../common.dart';
import '../utils/http_service.dart' as http;
import 'platform_model.dart';
import 'rdgen_session_work_groups.dart';
import 'rdgen_organization_store.dart';
import 'rdgen_organization_api.dart';
import 'rdgen_organization_editor.dart';
import 'rdgen_organization_preflight.dart';
import 'rdgen_work_group_origin.dart';

String rdgenServerDeviceName(String id, String hostname) {
  final accessible = gFFI.groupModel.peers.where((peer) => peer.id == id);
  if (accessible.isNotEmpty) {
    final alias = accessible.first.alias.trim();
    return alias.isNotEmpty ? alias : hostname.isEmpty ? id : hostname;
  }
  try {
    final token = bind.mainGetLocalOption(key: 'access_token');
    final data = jsonDecode(bind.mainGetLocalOption(key: 'rdgen-session-title-peers-v1'));
    if (token.isNotEmpty && data['access_token'] == token) {
      final alias = data['peers']?[id]?['alias'];
      if (alias is String && alias.trim().isNotEmpty) return alias.trim();
    }
  } catch (_) { /* No authenticated server snapshot yet. */ }
  return hostname.isEmpty ? id : hostname;
}

Future<void> rdgenManageDevice(BuildContext context, String id, {bool aliasOnly = false}) async {
  final token = bind.mainGetLocalOption(key: 'access_token');
  if (token.isEmpty || bind.isDisableAccount()) return;
  try {
    final launchContext = Navigator.of(context).context;
    final origin = RdgenWorkGroupOrigin.read(context);
    final base = Uri.parse(await bind.mainGetApiServer());
    final api = rdgenStoredOrganizationApi(base, id, (method, uri, body) async {
      if (token != bind.mainGetLocalOption(key: 'access_token') ||
          base.toString() != await bind.mainGetApiServer()) throw RdgenOrganizationApiError(401);
      final headers = {'Authorization': 'Bearer $token', 'Accept': 'application/json', 'Content-Type': 'application/json'};
      final reply = method == 'POST' ? await http.post(uri, headers: headers, body: body)
        : method == 'PUT' ? await http.put(uri, headers: headers, body: body)
        : await http.get(uri, headers: headers);
      if (token != bind.mainGetLocalOption(key: 'access_token')) throw RdgenOrganizationApiError(401);
      return WorkGroupReply(reply.statusCode, reply.body);
    });
    if (aliasOnly) {
      await api.readAlias();
      if (!api.canSetAlias) throw RdgenOrganizationApiError(403);
      await rdgenEditDeviceAlias(gFFI.dialogManager, api);
      return;
    }
    int? selected;
    final decision = await rdgenEditOrganization(manager: gFFI.dialogManager, api: api,
      boundChoices: const [], origin: origin, loadAlias: api.readAlias,
      loadBound: () async {
        final reply = await api.request('GET', api.uri('devices/${Uri.encodeComponent(id)}/work-groups'), null);
        if (reply.code != 200) throw RdgenOrganizationApiError(reply.code);
        return WorkGroupSession.choices(jsonDecode(reply.body));
      }, save: (group, attach) async {
        if (attach) await api.attach(group);
        selected = group;
      });
    if (decision == RdgenOrganizationDecision.saved && selected != null && launchContext.mounted &&
        token == bind.mainGetLocalOption(key: 'access_token') && base.toString() == await bind.mainGetApiServer()) {
      final intent = RdgenOrganizationIntent(supported: true, groupId: selected);
      await runZoned(() => connect(launchContext, id), zoneValues: intent.zoneValues);
    }
  } catch (error) { showToast(rdgenOrganizationError(error)); }
}
