import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import '../common.dart';
import 'platform_model.dart';
import '../utils/http_service.dart' as http;
import 'rdgen_organization_choices.dart';
import 'rdgen_session_work_groups.dart';
import 'rdgen_work_group_origin.dart';
import 'rdgen_organization_api.dart';
import 'rdgen_organization_editor.dart';

const rdgenPreflightCheckedKey = #statusdeskOrganizationPreflightChecked;
const rdgenPreflightDoneKey = #statusdeskOrganizationPreflightDone;
bool get rdgenPreflightChecked => Zone.current[rdgenPreflightCheckedKey] == true;
bool get rdgenPreflightDone => Zone.current[rdgenPreflightDoneKey] == true;

class RdgenOrganizationIntent {
  final bool proceed;
  final bool supported;
  final int? groupId;
  const RdgenOrganizationIntent({this.proceed = true, this.supported = false, this.groupId});
  Map<Object, Object?> get zoneValues => {
    rdgenPreflightCheckedKey: true,
    rdgenPreflightDoneKey: supported,
    rdgenWorkGroupZoneKey: supported ? groupId : rdgenLaunchingWorkGroup,
  };
}

Future<RdgenOrganizationIntent> rdgenOrganizationPreflight(String id) async {
  final token = bind.mainGetLocalOption(key: 'access_token');
  if (token.isEmpty || bind.isDisableAccount()) return const RdgenOrganizationIntent();
  try {
    final base = (await bind.mainGetApiServer()).replaceFirst(RegExp(r'/$'), '');
    final api = RdgenOrganizationApi(Uri.parse(base), id.replaceAll(' ', ''),
      (method, uri, body) async {
        if (token != bind.mainGetLocalOption(key: 'access_token')) throw RdgenOrganizationApiError(401);
        final headers = {'Authorization': 'Bearer $token', 'Accept': 'application/json', 'Content-Type': 'application/json'};
        final response = method == 'POST'
          ? await http.post(uri, headers: headers, body: body)
          : await http.get(uri, headers: headers);
        if (token != bind.mainGetLocalOption(key: 'access_token')) throw RdgenOrganizationApiError(401);
        return WorkGroupReply(response.statusCode, response.body, retryAfter: response.headers['retry-after']);
      });
    final response = await api.request('GET', api.uri('devices/${Uri.encodeComponent(api.peerId)}/work-groups'), null);
    if (token != bind.mainGetLocalOption(key: 'access_token')) {
      return const RdgenOrganizationIntent(proceed: false);
    }
    if (response.code != 200) return const RdgenOrganizationIntent();
    final decoded = jsonDecode(response.body);
    if (decoded is! Map<String, dynamic> || decoded['groups'] is! List) {
      return const RdgenOrganizationIntent();
    }
    final groups = WorkGroupSession.choices(decoded);
    if (groups.length == 1) return RdgenOrganizationIntent(supported: true, groupId: groups.single['id'] as int);
    if (groups.isEmpty) {
      try { await api.search(); } catch (_) { return const RdgenOrganizationIntent(supported: true); }
      if (!api.version2 || api.permissions['can_attach'] != true) return const RdgenOrganizationIntent(supported: true);
    }
    final origin = groups.any((g) => g['id'] == rdgenLaunchingWorkGroup) ? rdgenLaunchingWorkGroup : null;
    int? selected;
    final decision = await rdgenEditOrganization(manager: gFFI.dialogManager, api: api,
      boundChoices: groups, origin: origin,
      save: (id, needsAttachment) async {
        if (token != bind.mainGetLocalOption(key: 'access_token')) throw RdgenOrganizationApiError(401);
        if (needsAttachment) await api.attach(id);
        selected = id;
      });
    return decision == RdgenOrganizationDecision.cancel
      ? const RdgenOrganizationIntent(proceed: false)
      : RdgenOrganizationIntent(supported: true, groupId: selected);
  } catch (_) {
    debugPrint('Organization preflight unavailable; preserving the connection path');
    return const RdgenOrganizationIntent();
  }
}
