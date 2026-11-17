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
import 'rdgen_organization_store.dart';
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
    final api = rdgenStoredOrganizationApi(Uri.parse(base), id.replaceAll(' ', ''),
      (method, uri, body) async {
        if (token != bind.mainGetLocalOption(key: 'access_token')) throw RdgenOrganizationApiError(401);
        final headers = {'Authorization': 'Bearer $token', 'Accept': 'application/json', 'Content-Type': 'application/json'};
        final response = method == 'POST'
          ? await http.post(uri, headers: headers, body: body)
          : method == 'PUT' ? await http.put(uri, headers: headers, body: body)
          : await http.get(uri, headers: headers);
        if (token != bind.mainGetLocalOption(key: 'access_token')) throw RdgenOrganizationApiError(401);
        return WorkGroupReply(response.statusCode, response.body, retryAfter: response.headers['retry-after']);
      });
    var supported = false;
    if (isDesktop) await windowOnTop(null);
    int? selected;
    final decision = await rdgenEditOrganization(manager: gFFI.dialogManager, api: api,
      boundChoices: const [], origin: rdgenLaunchingWorkGroup, preflight: true,
      loadAlias: api.readAlias,
      loadBound: () async {
        final response = await api.request('GET',
          api.uri('devices/' + Uri.encodeComponent(api.peerId) + '/work-groups'), null);
        if (response.code != 200) throw RdgenOrganizationApiError(response.code);
        final decoded = jsonDecode(response.body);
        if (decoded is! Map<String, dynamic> || decoded['groups'] is! List) {
          throw FormatException('Unsupported device work-groups response');
        }
        supported = true;
        return WorkGroupSession.choices(decoded);
      },
      save: (id, needsAttachment) async {
        if (token != bind.mainGetLocalOption(key: 'access_token')) throw RdgenOrganizationApiError(401);
        if (needsAttachment) await api.attach(id);
        selected = id;
      });
    if (token != bind.mainGetLocalOption(key: 'access_token') ||
        base != (await bind.mainGetApiServer()).replaceFirst(RegExp(r'/$'), '')) {
      return const RdgenOrganizationIntent(proceed: false);
    }
    return decision == RdgenOrganizationDecision.cancel
      ? const RdgenOrganizationIntent(proceed: false)
      : RdgenOrganizationIntent(supported: supported, groupId: selected);
  } catch (_) {
    debugPrint('Organization preflight unavailable; preserving the connection path');
    return const RdgenOrganizationIntent();
  }
}
