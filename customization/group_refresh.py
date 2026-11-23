"""Desktop-only refresh over unchanged client APIs."""
from pathlib import Path


def add_group_refresh(root, edits, replace):
    model = 'flutter/lib/models/group_model.dart'
    replace(model, "import 'dart:convert';", """import 'dart:convert';
import 'dart:async';
import 'rdgen_group_refresh.dart';
import 'rdgen_organization_data.dart';
import 'rdgen_device_refresh.dart';""")
    replace(model, '  Future<void> pull({force = true, quiet = false}) async {', """  final _rdgenRefresh = RdgenGroupRefresh();
  late final rdgenOrganizations = RdgenOrganizationData();
  String? _rdgenToken;
  String? _rdgenServer;

  Future<void> pull({force = true, quiet = false, bool rdgenCatalog = false}) async {
    if (!isDesktop) return _rdgenOriginalPull(force: force, quiet: quiet);
    if (bind.isDisableGroupPanel() || !gFFI.userModel.isLogin) return;
    final token = bind.mainGetLocalOption(key: 'access_token');
    final server = await bind.mainGetApiServer();
    return _rdgenRefresh.run('$server\\n$token', () async {
      final changed = _rdgenToken != token || _rdgenServer != server;
      if (_rdgenToken != null && changed) await reset();
      _rdgenToken = token;
      _rdgenServer = server;
      await loadCache();
      await Future.wait<void>([
        _rdgenOriginalPull(force: force || changed, quiet: quiet),
        rdgenOrganizations.reload(force: rdgenCatalog),
      ]);
      if (initialized && token == bind.mainGetLocalOption(key: 'access_token') &&
          server == await bind.mainGetApiServer() && _statusCode != 401) _saveCache();
    }, catalog: rdgenCatalog);
  }

  Future<void> _rdgenOriginalPull({force = true, quiet = false}) async {""")
    replace(model, '  Future<void> loadCache() async {', """  Future<void>? _rdgenCacheLoading;
  Future<void> loadCache() {
    if (!isDesktop) return _rdgenOriginalLoadCache();
    // main.dart calls this before restoring the account; do not consume its one-shot read.
    if (!gFFI.userModel.isLogin) return Future<void>.value();
    return _rdgenCacheLoading ??= _rdgenOriginalLoadCache().whenComplete(() {
      _rdgenCacheLoading = null;
    });
  }
  Future<void> _rdgenOriginalLoadCache() async {""")
    replace(model, '    initialized = true;', """    if (isDesktop && (_rdgenToken != bind.mainGetLocalOption(key: 'access_token') ||
        _rdgenServer != await bind.mainGetApiServer())) return;
    initialized = true;""")
    replace(model, '    deviceGroups.value = tmpDeviceGroups;', """    if (isDesktop && (_rdgenToken != bind.mainGetLocalOption(key: 'access_token') ||
        _rdgenServer != await bind.mainGetApiServer())) return;
    deviceGroups.value = tmpDeviceGroups;""")
    replace(model, '    final api = "${await bind.mainGetApiServer()}/api/device-group/accessible";', """    if (isDesktop && _rdgenRefresh.catalogFresh) {
      tmpDeviceGroups.addAll(deviceGroups);
      return true;
    }
    final api = "${await bind.mainGetApiServer()}/api/device-group/accessible";""")
    path = root/model
    source = edits[path]
    if source.count('      final pageSize = 100;') != 3:
        raise ValueError('Incompatible group pagination')
    source = source.replace('      final pageSize = 100;', '      final pageSize = isDesktop ? 500 : 100;')
    source = source.replace('        final resp = await http.get(uri, headers: getHttpHeaders());',
        """        final requestToken = bind.mainGetLocalOption(key: 'access_token');
        final resp = await http.get(uri, headers: getHttpHeaders());
        if (isDesktop && requestToken != bind.mainGetLocalOption(key: 'access_token')) return false;""")
    anchor = '      } while (current * pageSize < total);\n      return true;'
    if source.count(anchor) not in (2, 3): raise ValueError('Incompatible group completion anchor')
    source = source.replace(anchor, """      } while (current * pageSize < total);
      if (isDesktop && _rdgenServer == await bind.mainGetApiServer() &&
          _rdgenToken == bind.mainGetLocalOption(key: 'access_token')) {
        deviceGroups.value = List<DeviceGroupPayload>.of(tmpDeviceGroups);
        _rdgenRefresh.catalogAt = DateTime.now();
      }
      return true;""", 1)
    if source.count('    initialized = false;\n    groupLoadError') != 1: raise ValueError('Incompatible group reset anchor')
    source = source.replace('    initialized = false;\n    groupLoadError', """    initialized = false;
    _cacheLoadOnceFlag = false;
    _rdgenRefresh.catalogAt = null;
    if (isDesktop) rdgenOrganizations.reset();
    groupLoadError""", 1)
    edits[path] = source
    # Keep the mobile sequence unchanged; desktop requests have independent URLs.
    start = source.index('    List<DeviceGroupPayload> tmpDeviceGroups =')
    end = source.index('    if (isDesktop && (_rdgenToken', start)
    original_fetch = source[start:end]
    declarations = '''    List<DeviceGroupPayload> tmpDeviceGroups = List.empty(growable: true);
    List<UserPayload> tmpUsers = List.empty(growable: true);
    List<Peer> tmpPeers = List.empty(growable: true);
'''
    mobile_fetch = original_fetch
    for declaration in declarations.splitlines(keepends=True):
        if mobile_fetch.count(declaration) != 1:
            raise ValueError('Incompatible accessible-list declarations')
        mobile_fetch = mobile_fetch.replace(declaration, '', 1)
    edits[path] = source[:start] + declarations + '''    if (isDesktop) {
      _statusCode = 200;
      final results = await Future.wait<bool>([
        _getDeviceGroups(tmpDeviceGroups),
        _getUsers(tmpUsers),
        _getPeers(tmpPeers),
      ]);
      if (_statusCode == 401 || !results[1] || !results[2]) return;
      if (!results[0]) tmpDeviceGroups..clear()..addAll(deviceGroups);
      tmpDeviceGroups.sort((a, b) => a.name.compareTo(b.name));
    } else {
''' + mobile_fetch + '''    }
''' + source[end:]
    source = edits[path]
    if source.count('        _statusCode = resp.statusCode;') != 3:
        raise ValueError('Incompatible accessible-list HTTP status anchors')
    edits[path] = source.replace('        _statusCode = resp.statusCode;', '''        // An overlapping successful request must not erase an auth failure.
        if (!isDesktop || _statusCode != 401) _statusCode = resp.statusCode;''')
    replace(model, '      _saveCache();', '      if (!isDesktop) _saveCache();')
    replace(model, '      bind.mainSaveGroup(json: jsonEncode(map));', '''      if (isDesktop) {
        unawaited(bind.mainSetLocalOption(key: 'rdgen-accessible-cache-v1',
            value: jsonEncode(map)).catchError((Object _) {
          debugPrint('Failed to save accessible-device cache');
        }));
      } else {
        bind.mainSaveGroup(json: jsonEncode(map));
      }''')
    replace(model, '      final cache = await bind.mainLoadGroup();', '''      final cache = isDesktop
          ? bind.mainGetLocalOption(key: 'rdgen-accessible-cache-v1')
          : await bind.mainLoadGroup();''')
    replace(model, '        _callbackPeerUpdate();', '''        _callbackPeerUpdate();
        if (isDesktop) platformFFI.tryHandle({'name': LoadEvent.group});''')
    replace(model, '    await bind.mainClearGroup();', '''    if (isDesktop) await bind.mainSetLocalOption(key: 'rdgen-accessible-cache-v1', value: '');
    await bind.mainClearGroup();''')
    peer_cache = "e.toGroupCacheJson()..['alias'] = e.alias" if "e.toGroupCacheJson()..['alias']" in edits[path] else 'e.toGroupCacheJson()'
    replace(model, "'peers': peers.map((e) => " + peer_cache + ").toList()", """'peers': peers.map((e) => isDesktop
            ? {...e.toGroupCacheJson(), 'loginName': e.loginName, 'alias': e.alias}
            : (""" + peer_cache + ")).toList()")
    replace(model, '    peersModel = Peers(', """    if (isDesktop) rdgenRefreshVisibleDevice = (id) async {
      final peer = peers.where((p) => p.id == id).toList();
      await rdgenOrganizations.refreshDevice(id);
      if (peer.isNotEmpty) {
        final alias = await rdgenOrganizations.readAlias(id);
        if (alias != null) {
          peer.single.alias = alias;
          peers.refresh();
          _callbackPeerUpdate();
          _saveCache();
        }
      }
    };
    peersModel = Peers(""")
    replace(model, '        "access_token": bind.mainGetLocalOption(key: \'access_token\'),', '''        "access_token": bind.mainGetLocalOption(key: 'access_token'),
        'rdgen_server': _rdgenServer,
        'rdgen_organizations': isDesktop ? rdgenOrganizations.cachedGroups : null,''')
    replace(model, "      if (data == null || data['access_token'] != access_token) return;", """      if (data == null || data['access_token'] != access_token) return;
      if (isDesktop && (data['rdgen_server'] != await bind.mainGetApiServer() ||
          access_token != bind.mainGetLocalOption(key: 'access_token'))) return;
      if (isDesktop) rdgenOrganizations.restoreCachedGroups(data['rdgen_organizations'], access_token);""")
    replace('flutter/lib/models/user_model.dart', '    _updateLocalUserInfo();', '''    _updateLocalUserInfo();
    if (isDesktop) unawaited(gFFI.groupModel.loadCache());''')
    page = root/'flutter/lib/common/widgets/peer_tab_page.dart'
    text = edits.get(page, page.read_text(encoding='utf-8'))
    text = text.replace('groupModel.pull(force: hint == null)',
        'groupModel.pull(force: hint == null, rdgenCatalog: hint == null)')
    edits[page] = text
    for name in ['group_refresh', 'device_refresh', 'organization_data',
                 'organization_catalog', 'session_work_groups']:
        edits[root/f'flutter/lib/models/rdgen_{name}.dart'] = Path(__file__).with_name(name+'.dart').read_text(encoding='utf-8')
