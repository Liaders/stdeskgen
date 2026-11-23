import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from apply_profile import apply
import test_slim_ui


class OrganizationsTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('dart'), 'Dart SDK is available on CI')
    def test_parallel_lists_preserve_failure_and_auth_handling(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            test_slim_ui.SlimUiTests.fixture(self, root)
            apply(root, '1.5.1', {'schema_version': 1, 'organizations': True})
            model = (root/'flutter/lib/models/group_model.dart').read_text(encoding='utf-8')
            start = model.index('    List<DeviceGroupPayload> tmpDeviceGroups =')
            fetch = model[start:model.index('    if (isDesktop && (_rdgenToken', start)]
            status = next(line for line in model.splitlines()
                          if 'if (!isDesktop || _statusCode != 401)' in line)
            harness = """import 'dart:async';
void check(bool value) { if (!value) throw StateError('Accessible list refresh'); }
class Row { final String name; Row(this.name); }
typedef DeviceGroupPayload = Row;
typedef UserPayload = Row;
typedef Peer = Row;
class Response { final int statusCode; Response(this.statusCode); }
class Model {
  bool isDesktop = true, published = false;
  int _statusCode = 200, started = 0;
  final deviceGroups = <Row>[Row('cached')];
  final groups = Completer<bool>(), users = Completer<bool>(), peers = Completer<bool>();
  Future<bool> load(List<Row> rows, Completer<bool> reply) {
    started++; rows.add(Row('new')); return reply.future;
  }
  Future<bool> _getDeviceGroups(List<Row> rows) => load(rows, groups);
  Future<bool> _getUsers(List<Row> rows) => load(rows, users);
  Future<bool> _getPeers(List<Row> rows) => load(rows, peers);
  void status(int code) { final resp = Response(code);
""" + status + """
  }
  Future<void> pull() async {
""" + fetch + """
    published = tmpUsers.single.name == 'new' && tmpPeers.single.name == 'new';
  }
}
Future<void> main() async {
  for (final failure in ['none', 'users', 'auth']) {
    final model = Model();
    final pending = model.pull();
    check(model.started == 3); // Devices can load while the group directory is pending.
    if (failure == 'auth') { model.status(401); model.status(200); }
    model.peers.complete(true);
    model.users.complete(failure != 'users');
    model.groups.complete(true);
    await pending;
    check(model.published == (failure == 'none'));
    if (failure == 'auth') check(model._statusCode == 401);
  }
  final mobile = Model()..isDesktop = false;
  final pending = mobile.pull();
  check(mobile.started == 1);
  mobile.groups.complete(true);
  await Future<void>.delayed(Duration.zero);
  check(mobile.started == 2);
  mobile.users.complete(true);
  await Future<void>.delayed(Duration.zero);
  mobile.peers.complete(true);
  await pending;
  check(mobile.published);
}
"""
            path = root/'parallel_refresh_test.dart'
            path.write_text(harness, encoding='utf-8')
            subprocess.run([shutil.which('dart'), str(path)], check=True,
                           capture_output=True, timeout=60)

    def test_groups_only_with_independent_filters_and_preserved_tab_preferences(self):
        for colleagues in (False, True):
            with self.subTest(colleagues=colleagues), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                test_slim_ui.SlimUiTests.fixture(self, root)
                apply(root, '1.5.1', {'schema_version': 1, 'organizations': True,
                                     'colleagues': colleagues, 'resizable_panels': True})
                view = (root/'flutter/lib/common/widgets/rdgen_organizations.dart').read_text(encoding='utf-8')
                self.assertNotIn('_buildUserItem', view)
                self.assertNotIn('groupModel.users', view)
                self.assertIn('itemCount: deviceGroupItems.length', view)
                self.assertIn('organizations.any((group)', view)
                self.assertIn('group.peerIds.contains(peer.id)', view)
                self.assertIn('group.selectionKey == selected', view)
                self.assertIn('groupId: origins.first.id!', view)
                self.assertIn('_organizationData.groups', view)
                self.assertIn("final selectedAccessibleItemName = ''.obs;", view)
                self.assertIn('rdgen-panel-organizations-width-v1', view)
                self.assertEqual(view.count("key: ValueKey('$selected/$search')"), 2)
                model = (root/'flutter/lib/models/peer_tab_model.dart').read_text(encoding='utf-8')
                index = 6 if colleagues else 5
                self.assertIn(f'maxTabCount = {index+1};', model)
                self.assertIn(f'if (decodeList.length == {index}) decodeList.add(true);', model)
                self.assertIn(f'if (decodeList.length == {index}) decodeList.add({index});', model)
                self.assertIn('Icons.apartment_outlined', model)
                self.assertIn('Организации', (root/'src/lang/ru.rs').read_text(encoding='utf-8'))
                if shutil.which('dart'):
                    for name in ['common/widgets/rdgen_organizations.dart', 'common/widgets/peer_tab_page.dart', 'models/peer_tab_model.dart', 'models/rdgen_organization_catalog.dart', 'models/rdgen_organization_data.dart', 'models/rdgen_work_group_origin.dart']:
                        subprocess.run(['dart','format','--output=none',str(root/'flutter/lib'/name)],check=True,capture_output=True,timeout=60)

    def test_initial_order_migrates_once_without_touching_visibility(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            test_slim_ui.SlimUiTests.fixture(self, root)
            apply(root, '1.5.1', {'schema_version': 1, 'organizations': True, 'colleagues': True})
            model = (root/'flutter/lib/models/peer_tab_model.dart').read_text(encoding='utf-8')
            start = model.index('    // rdgen initial tab order')
            constructor = model[start:model.index('    // init currentTab', start)]
            start = model.index('  Future<void> _rdgenSaveInitialTabOrder()')
            method = model[start:model.index('  setCurrentTab(int index)', start)]
            self.assertIn('orders.setAll(0, [0, 1, 6, 5, 2, 4, 3]);', constructor)
            self.assertNotIn('_isVisible', constructor+method)
            self.assertLess(method.index('k: kOptionPeerTabOrder'), method.index("v: 'Y'"))
            if not shutil.which('dart'): return
            harness = """import 'dart:convert';
const kOptionPeerTabOrder = 'order';
void debugPrint(Object? message) {}
class Bind {
  final values = <String,String>{'visible':'[false,true,false,true,true,false,true]'};
  String getLocalFlutterOption({required String k}) => values[k] ?? '';
  Future<void> setLocalFlutterOption({required String k, required String v}) async { values[k] = v; }
}
final bind = Bind();
class Model {
  final List<int> orders;
  Model(List<int> saved) : orders = List.of(saved) {
""" + constructor + """  }
""" + method + """}
Future<void> main() async {
  final old = Model([6,5,4,3,2,1,0]);
  if (old.orders.join(',') != '0,1,6,5,2,4,3') throw StateError('initial order');
  await Future<void>.delayed(Duration.zero);
  if (bind.values['rdgen-peer-tab-order-v1-7'] != 'Y') throw StateError('marker');
  if (bind.values['order'] != '[0,1,6,5,2,4,3]') throw StateError('saved order');
  final custom = [1,0,6,3,4,2,5];
  final restarted = Model(custom);
  if (restarted.orders.join(',') != custom.join(',')) throw StateError('manual order lost');
  if (bind.values['visible'] != '[false,true,false,true,true,false,true]') throw StateError('visibility changed');
}
"""
            path = root/'tab_order_test.dart'
            path.write_text(harness, encoding='utf-8')
            subprocess.run(['dart','run',str(path)],check=True,capture_output=True,timeout=60)

    def test_omitted_organizations_leave_original_tabs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            test_slim_ui.SlimUiTests.fixture(self, root)
            model = root/'flutter/lib/models/peer_tab_model.dart'
            original = model.read_bytes()
            apply(root, '1.5.1', {'schema_version': 1})
            self.assertEqual(original, model.read_bytes())
            self.assertFalse((root/'flutter/lib/common/widgets/rdgen_organizations.dart').exists())
