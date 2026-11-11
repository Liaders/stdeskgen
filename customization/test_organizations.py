import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from apply_profile import apply
import test_slim_ui


class OrganizationsTests(unittest.TestCase):
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
                self.assertIn('gFFI.groupModel.deviceGroups.any((group)', view)
                self.assertIn('group.name == peer.device_group_name', view)
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
                    for name in ['common/widgets/rdgen_organizations.dart', 'common/widgets/peer_tab_page.dart', 'models/peer_tab_model.dart']:
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
