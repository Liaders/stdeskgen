from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from apply_profile import apply
import test_slim_ui


class NewDevicesTests(unittest.TestCase):
    def test_rollout_resets_tabs_once_and_keeps_icon_preference(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            test_slim_ui.SlimUiTests().fixture(root)
            apply(root, '1.5.1', {'schema_version': 1, 'organizations': True,
                                 'colleagues': True, 'navigation': 'icons'})
            model = (root/'flutter/lib/models/peer_tab_model.dart').read_text(encoding='utf-8')
            start = model.index("    if (bind.getLocalFlutterOption(k: 'rdgen-peer-tabs-new-devices-v3')")
            constructor = model[start:model.index('    // init currentTab', start)]
            start = model.index('  Future<void> _rdgenSaveNewDeviceTabs()')
            method = model[start:model.index('  setCurrentTab(int index)', start)]
            harness = """import 'dart:convert';
const kOptionPeerTabOrder = 'order', kOptionPeerTabVisible = 'visible', kOptionPeerCardUiType = 'view';
void debugPrint(Object? x) {}
class Bind {
 final values = <String,String>{'rdgen-navigation-style-v1':'icons', 'rdgen-peer-tabs-new-devices-v1':'Y', 'rdgen-peer-tabs-new-devices-v2':'Y'};
 String getLocalFlutterOption({required String k}) => values[k] ?? '';
 Future<void> setLocalFlutterOption({required String k, required String v}) async { values[k]=v; }
}
final bind=Bind();
class Model {
 final orders=List.generate(8,(i)=>i);
 final _isVisible=List.filled(8,true);
 Model() {
""" + constructor + "\n}\n" + method + """}
Future<void> main() async {
 final m=Model();
 await Future<void>.delayed(Duration.zero);
 if(m.orders.join(',')!='0,3,1,6,5,7,2,4') throw StateError('order');
 if(m._isVisible[2] || m._isVisible[4]) throw StateError('visibility');
 if(bind.values['rdgen-navigation-style-v1']!='icons') throw StateError('icons lost');
 if(bind.values['view']!='2') throw StateError('list view missing');
 bind.values['view']='0';
 final next=Model();
 if(next.orders.join(',')!='0,1,2,3,4,5,6,7') throw StateError('migration repeated');
 await Future<void>.delayed(Duration.zero);
 if(bind.values['view']!='0') throw StateError('view preference reset again');
}
"""
            path=root/'rollout.dart'; path.write_text(harness,encoding='utf-8')
            subprocess.run([shutil.which('dart'),str(path)],check=True,capture_output=True,timeout=60)
            page=(root/'flutter/lib/common/widgets/peer_tab_page.dart').read_text(encoding='utf-8')
            self.assertIn('Icons.auto_awesome',model)
            self.assertIn('RdgenNewDeviceCount(count: newCount, selected: selected)',page)
            self.assertIn('Color(0xFFD29922)',page)
            self.assertIn('Color(0xFFEAB84B)',page)
            self.assertIn('fontWeight: FontWeight.w700',(root/'flutter/lib/common/widgets/rdgen_new_devices.dart').read_text(encoding='utf-8'))
            self.assertIn('model.currentTab == PeerTabIndex.recent.index || model.currentTab == 7',page)
            view=(root/'flutter/lib/common/widgets/peers_view.dart').read_text(encoding='utf-8')
            self.assertIn('height: 140 + widget.rdgenCardFooterHeight',view)
            self.assertIn('height: 42 + widget.rdgenCardFooterHeight',view)
            card=(root/'flutter/lib/common/widgets/rdgen_new_devices.dart').read_text(encoding='utf-8')
            self.assertNotIn('Positioned(',card)
            self.assertIn('isConfirmedUngrouped',card)
            for name in ['common/widgets/peer_tab_page.dart','common/widgets/peers_view.dart','common/widgets/rdgen_new_devices.dart','models/peer_model.dart']:
                subprocess.run([shutil.which('dart'),'format','--output=none',str(root/'flutter/lib'/name)],check=True,capture_output=True,timeout=60)

    def test_creation_time_filter_age_and_newest_first(self):
        text=Path(__file__).with_name('new_devices.dart').read_text(encoding='utf-8')
        start=text.index('bool rdgenIsNewDevice')
        end=text.index('/// A slow tick')
        code=text[start:end].replace("final language = WidgetsBinding.instance.platformDispatcher.locale.languageCode;", "final language = 'ru';")
        harness="""class Peer { DateTime? rdgenCreatedAt; Peer(this.rdgenCreatedAt); }
String translate(String key) => key;
"""+code+"""
void main() {
 final now=DateTime.utc(2026,11,25,12);
 if(rdgenIsNewDevice(Peer(null),now)) throw StateError('missing timestamp');
 if(rdgenIsNewDevice(Peer(now.add(Duration(seconds:1))),now)) throw StateError('future');
 if(rdgenIsNewDevice(Peer(now.subtract(Duration(hours:24))),now)) throw StateError('expired');
 if(!rdgenIsNewDevice(Peer(now.subtract(Duration(hours:23,minutes:59))),now)) throw StateError('recent');
 if(rdgenDeviceAge(now.subtract(Duration(seconds:59)),now)!='Just now') throw StateError('just now');
 if(rdgenDeviceAge(now.subtract(Duration(minutes:21)),now)!='21 минуту назад') throw StateError('minutes');
 if(rdgenDeviceAge(now.subtract(Duration(hours:3)),now)!='3 часа назад') throw StateError('hours');
}
"""
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'ages.dart'; path.write_text(harness,encoding='utf-8')
            subprocess.run([shutil.which('dart'),str(path)],check=True,capture_output=True,timeout=60)

    def test_assignment_refreshes_view_even_without_alias_and_loads_missing_peer(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            test_slim_ui.SlimUiTests().fixture(root)
            apply(root,'1.5.1',{'schema_version':1,'organizations':True})
            source=(root/'flutter/lib/models/group_model.dart').read_text(encoding='utf-8')
            start=source.index('      await rdgenOrganizations.refreshDevice(id);')
            body=source[start:source.index('\n    };',start)]
            harness="""import 'dart:async';
class Peer { final String id; String alias=''; Peer(this.id); }
class Peers extends Iterable<Peer> {
 final rows=<Peer>[]; int updates=0;
 Iterator<Peer> get iterator=>rows.iterator;
 void refresh(){updates++;}
}
class Orgs {
 int refreshed=0;
 Future<void> refreshDevice(String id) async {refreshed++;}
 Future<String?> readAlias(String id) async => null;
}
class Platform { int events=0; void tryHandle(Object x){events++;} }
class LoadEvent { static const group='group'; }
class Model {
 final peers=Peers(); final rdgenOrganizations=Orgs(); final platformFFI=Platform();
 int pulls=0,callbacks=0,saves=0;
 Future<void> pull({bool force=false}) async {pulls++; peers.rows.add(Peer('new'));}
 void _callbackPeerUpdate(){callbacks++;}
 void _saveCache(){saves++;}
 Future<void> changed(String id) async {
"""+body+"""
 }
}
Future<void> main() async {
 final m=Model(); m.peers.rows.add(Peer('known'));
 await m.changed('known');
 if(m.pulls!=0 || m.callbacks!=1 || m.saves!=1 || m.platformFFI.events!=1) throw StateError('known device not refreshed');
 await m.changed('new');
 if(m.pulls!=1 || !m.peers.any((p)=>p.id=='new') || m.callbacks!=2) throw StateError('newly accessible device missing');
}
"""
            path=root/'assignment.dart'; path.write_text(harness,encoding='utf-8')
            subprocess.run([shutil.which('dart'),str(path)],check=True,capture_output=True,timeout=60)


if __name__ == '__main__': unittest.main()
