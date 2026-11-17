"""Desktop-only refresh over unchanged client APIs."""
from pathlib import Path


def add_group_refresh(root, edits, replace):
    model = 'flutter/lib/models/group_model.dart'
    replace(model, "import 'dart:convert';", """import 'dart:convert';
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
      await _rdgenOriginalPull(force: force || changed, quiet: quiet);
      if (token == bind.mainGetLocalOption(key: 'access_token') &&
          server == await bind.mainGetApiServer()) {
        await rdgenOrganizations.reload(force: rdgenCatalog);
      }
    }, catalog: rdgenCatalog);
  }

  Future<void> _rdgenOriginalPull({force = true, quiet = false}) async {""")
    replace(model, '  Future<void> loadCache() async {', """  Future<void>? _rdgenCacheLoading;
  Future<void> loadCache() {
    if (!isDesktop) return _rdgenOriginalLoadCache();
    return _rdgenCacheLoading ??= _rdgenOriginalLoadCache().whenComplete(() {
      _rdgenCacheLoading = null;
    });
  }
  Future<void> _rdgenOriginalLoadCache() async {""")
    replace(model, '    if (!await _getDeviceGroups(tmpDeviceGroups)) {', """    if (!await _getDeviceGroups(tmpDeviceGroups)) {
      if (isDesktop) {
        tmpDeviceGroups..clear()..addAll(deviceGroups);
      }""")
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
    anchor = '      } while (current * pageSize < total);\\n      return true;'
    source = source.replace(anchor, """      } while (current * pageSize < total);
      if (isDesktop) _rdgenRefresh.catalogAt = DateTime.now();
      return true;""", 1)
    source = source.replace('    initialized = false;\\n    groupLoadError', """    initialized = false;
    _cacheLoadOnceFlag = false;
    _rdgenRefresh.catalogAt = null;
    if (isDesktop) rdgenOrganizations.reset();
    groupLoadError""", 1)
    edits[path] = source
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
        'rdgen_server': _rdgenServer,''')
    replace(model, "      if (data == null || data['access_token'] != access_token) return;", """      if (data == null || data['access_token'] != access_token) return;
      if (isDesktop && (access_token != bind.mainGetLocalOption(key: 'access_token') ||
          data['rdgen_server'] != await bind.mainGetApiServer())) return;""")
    page = root/'flutter/lib/common/widgets/peer_tab_page.dart'
    text = edits.get(page, page.read_text(encoding='utf-8'))
    text = text.replace('groupModel.pull(force: hint == null)',
        'groupModel.pull(force: hint == null, rdgenCatalog: hint == null)')
    edits[page] = text
    for name in ['group_refresh', 'device_refresh', 'organization_data',
                 'organization_catalog', 'session_work_groups']:
        edits[root/f'flutter/lib/models/rdgen_{name}.dart'] = Path(__file__).with_name(name+'.dart').read_text(encoding='utf-8')
