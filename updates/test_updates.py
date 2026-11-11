import importlib.util
import io
import tarfile
import shutil
import re
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))
from config import validate
from release import prepare, load_manifest

spec = importlib.util.spec_from_file_location('update_adapter', Path(__file__).with_name('apply.py'))
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


def checkout(root):
    source = Path(__file__).resolve().parents[2] / 'rustdesk'
    names = ['Cargo.toml', 'src/updater.rs', 'src/common.rs', 'src/ipc.rs',
             'src/ui_interface.rs', 'src/flutter_ffi.rs', 'src/ui/index.tis',
             'flutter/lib/desktop/pages/desktop_home_page.dart', 'src/lang']
    data = subprocess.check_output(['git','-c',f'safe.directory={source.as_posix()}',
        '-C',str(source),'archive',os.environ.get('RUSTDESK_TEST_REF','HEAD'),*names])
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        archive.extractall(root,filter='data')


class UpdateTests(unittest.TestCase):
    config = {'base_url': 'https://desk.status16.ru/client',
              'product': 'statusdesk', 'channel': 'test', 'revision': 2}

    def source(self, root):
        source = root / 'input'
        source.mkdir()
        receipt = {**self.config, 'schema': 2, 'platform': 'windows-x64', 'app_name': 'StatusDesk', 'version': '1.5.0'}
        (source / 'stdesk-update-build.json').write_text(json.dumps(receipt))
        binary = bytearray(256)
        binary[:2] = b'MZ'
        struct.pack_into('<I', binary, 0x3c, 128)
        binary[128:134] = b'PE\0\0\x64\x86'
        (source / 'client.exe').write_bytes(binary)
        return source

    def test_package_needs_no_keys_and_records_binary_integrity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = prepare(self.source(root), root / 'bundle', 'StatusDesk', '1.5.0', '123', 'abc')
            data = (root / 'bundle/channels/statusdesk/test/windows-x64.json').read_bytes()
            self.assertEqual(load_manifest(data), result)
            self.assertEqual(result['size'], 256)
            self.assertEqual(len(result['sha256']), 64)
            self.assertNotIn('signature', result)

    def test_catalog_preserves_other_platforms(self):
        from download_catalog import update
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            update(root, 'windows-x86', url='/client/downloads/x86.exe', version='1.5.0')
            update(root, 'macos-arm64', url='/client/downloads/mac.dmg', version='1.5.0')
            catalog = json.loads((root / 'downloads.json').read_text())
            self.assertEqual(set(catalog['items']), {'windows-x86', 'macos-arm64'})

    @unittest.skipIf(sys.platform == 'win32', 'Apache publication uses Linux file locking')
    def test_android_publication_preserves_desktop_and_rejects_wrong_architecture(self):
        import zipfile
        from publish_download import publish
        from download_catalog import update
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);public=root/'public';public.mkdir()
            update(public,'windows-x64',url='/client/old.exe',version='1.5.0.3')
            apk=root/'client.apk'
            with zipfile.ZipFile(apk,'w') as archive:
                archive.writestr('AndroidManifest.xml',b'fixture manifest')
                archive.writestr('lib/arm64-v8a/librustdesk.so',b'fixture library')
            with self.assertRaises(ValueError):publish(public,apk,'android-armv7','1.5.1.2')
            publish(public,apk,'android-arm64','1.5.1.2')
            items=json.loads((public/'downloads.json').read_text())['items']
            self.assertEqual(items['windows-x64'],{'url':'/client/old.exe','version':'1.5.0.3'})
            self.assertEqual(items['android-arm64']['version'],'1.5.1.2')
            self.assertEqual((public/items['android-arm64']['url'].removeprefix('/client/')).read_bytes(),apk.read_bytes())
            self.assertFalse((public/'channels').exists())

    def test_bad_configuration_and_unsupported_platform_fail(self):
        self.assertEqual(validate(self.config, platform='windows-x86'), self.config)
        for patch in ({'base_url': 'http://desk.status16.ru/client'}, {'revision': True}, {'product': '../other'}, {'public_key': 'obsolete'}):
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                validate({**self.config, **patch})
        with self.assertRaises(ValueError):
            validate(self.config, platform='linux')

    def test_adapter_is_opt_in_and_rejects_reapplying_without_partial_writes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            checkout(root)
            before = (root / 'src/updater.rs').read_bytes()
            adapter.apply(root, None)
            self.assertEqual(before, (root / 'src/updater.rs').read_bytes())
            adapter.apply(root, self.config)
            self.assertIn('return rdgen_update::check();', (root / 'src/updater.rs').read_text())
            generated = (root / 'src/rdgen_update.rs').read_text()
            self.assertNotIn('@INSTALL_VERIFIED_UPDATE@', generated)
            if 'version = "1.5.1"' in (root / 'Cargo.toml').read_text():
                self.assertIn('&path, &release.sha256)', generated)
            after = (root / 'src/updater.rs').read_bytes()
            with self.assertRaises(ValueError):
                adapter.apply(root, self.config)
            self.assertEqual(after, (root / 'src/updater.rs').read_bytes())

    def test_original_update_cards_use_service_channel_without_custom_panel(self):
        for platform in ('windows', 'windows-x86'):
            with self.subTest(platform=platform), tempfile.TemporaryDirectory() as temporary:
                root=Path(temporary); checkout(root)
                adapter.apply(root,self.config,platform)
                generated=(root/'src/rdgen_update.rs').read_text(encoding='utf-8')
                self.assertIn('if !manually && !config::Config::get_bool_option',generated)
                self.assertEqual(generated.count('Close active sessions before updating'),2)
                self.assertIn('RUNNING.compare_exchange',generated)
                self.assertIn('Update SHA-256 mismatch',generated)
                self.assertIn('let result = check_inner(true);',generated)
                inner=generated[generated.index('fn check_inner(manually: bool)'):]
                self.assertLess(inner.index('fetch_release()?'),inner.index('OPTION_ALLOW_AUTO_UPDATE'))
                self.assertLess(inner.index('fetch_release()?'),inner.index('has_no_active_conns()'))
                self.assertIn('timeout(Duration::from_secs(30))',generated)
                self.assertIn('manual_command(&name)',(root/'src/ipc.rs').read_text(encoding='utf-8'))
                self.assertIn('crate::ipc::get_config(key.as_ref())',(root/'src/ui_interface.rs').read_text(encoding='utf-8'))
                if sys.platform != 'win32' and shutil.which('rustfmt'):
                    for name in ['src/rdgen_update.rs','src/updater.rs','src/ipc.rs','src/ui_interface.rs','src/flutter_ffi.rs']:
                        subprocess.run(['rustfmt','--edition','2021','--emit','stdout','--config','skip_children=true',str(root/name)],check=True,capture_output=True,timeout=60)
                if platform=='windows-x86':
                    script=(root/'src/ui/index.tis').read_text(encoding='utf-8')
                    self.assertNotIn('class RdgenUpdateCard',script)
                    self.assertIn('class UpdateMe: Reactor.Component',script)
                    self.assertIn('event click $(#install-me) { rdgenInstallUpdate(); }',script)
                    self.assertIn('tmp = rdgenUpdateCardUrl();',script)
                    self.assertNotIn('rdgen-update-check',script)
                    self.assertIn('<InstallMe />',script)
                else:
                    card=root/'flutter/lib/models/rdgen_stock_update.dart'
                    home=root/'flutter/lib/desktop/pages/desktop_home_page.dart'
                    self.assertFalse((root/'flutter/lib/models/rdgen_update_card.dart').exists())
                    self.assertNotIn('RdgenUpdateCard',home.read_text(encoding='utf-8'))
                    self.assertIn("'Update', () { rdgenInstallUpdate(); }",home.read_text(encoding='utf-8'))
                    self.assertIn('await rdgenPollUpdateCard();',home.read_text(encoding='utf-8'))
                    self.assertNotIn('rdgen-update-check',card.read_text(encoding='utf-8'))
                    spec=importlib.util.spec_from_file_location('disable_stock_updates',Path(__file__).resolve().parents[1]/'customization/disable_update_notifications.py')
                    disable=importlib.util.module_from_spec(spec);spec.loader.exec_module(disable);disable.apply(root)
                    self.assertIn('updateUrl.startsWith(rdgenUpdatePrefix)',home.read_text(encoding='utf-8'))
                    if shutil.which('dart'):
                        for path in [card,root/'flutter/lib/desktop/pages/desktop_home_page.dart']:
                            subprocess.run(['dart','format','--output=none',str(path)],check=True,capture_output=True,timeout=60)
                        transport=re.sub(r'^import .*\n','',card.read_text(encoding='utf-8'),flags=re.M)
                        harness="""import 'dart:convert';
const isWindows=true;
final notices=<String>[];
String translate(String message)=>message;
void showToast(String message){ notices.add(message); }
class Value { String value=''; }
class Global { final updateUrl=Value(); }
final stateGlobal=Global();
class Bind {
 Map<String,dynamic> response={};
 bool mainIsInstalled()=>true;
 Future<String> mainGetCommon({required String key}) async => jsonEncode(response);
}
final bind=Bind();
"""+transport+"""
Future<void> main() async {
 bind.response={'status':'available','version':'1.5.1.99'};
 await rdgenPollUpdateCard();
 if(stateGlobal.updateUrl.value!=rdgenUpdatePrefix+'1.5.1.99') throw StateError('no original card');
 bind.response={'status':'error','version':'1.5.1.99'};
 await rdgenPollUpdateCard();
 if(stateGlobal.updateUrl.value.isEmpty) throw StateError('retry card lost');
 bind.response={'status':'current','version':''};
 await rdgenPollUpdateCard();
 if(stateGlobal.updateUrl.value.isNotEmpty) throw StateError('obsolete card');
 bind.response={'status':'available','version':'1.5.1.99'}; await rdgenPollUpdateCard();
 bind.response={'status':'downloading','version':'1.5.1.99'}; await rdgenInstallUpdate();
 bind.response={'status':'error','version':'1.5.1.99','message':'Close active sessions before updating'};
 await rdgenPollUpdateCard();
 if(notices.last!='Close active sessions before updating') throw StateError('failure hidden');
}
"""
                        test=root/'stock_card_test.dart';test.write_text(harness,encoding='utf-8')
                        subprocess.run(['dart','run',str(test)],check=True,capture_output=True,timeout=60)


    def test_schedule_checks_every_half_hour_including_busy_sessions_and_failures(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); checkout(root); adapter.apply(root,self.config)
            source=(root/'src/updater.rs').read_text(encoding='utf-8')
            start=source.index('    if let Err(e) = check_update(false)')
            body=source[start:source.index('    loop {',start)]
            self.assertIn('let mut check_interval = RETRY_INTERVAL;',body)
            schedule=source[source.index('fn start_auto_update_check_'):source.index('fn check_update(manually:')]
            self.assertNotIn('DUR_ONE_DAY',schedule)
            self.assertNotIn('has_no_active_conns()',schedule)
            check=source[source.index('fn check_update(manually:'):]
            self.assertLess(check.index('return rdgen_update::check();'),check.index('OPTION_ALLOW_AUTO_UPDATE'))
            if sys.platform=='win32' or not shutil.which('rustc'): return
            harness=r"""extern crate self as log;
#[macro_export] macro_rules! error { ($($t:tt)*) => { () }; }
use std::time::{Duration,Instant};
use std::sync::atomic::{AtomicBool,AtomicUsize,Ordering};
static ACTIVE: AtomicBool=AtomicBool::new(false);
static ERROR: AtomicBool=AtomicBool::new(false);
static CALLS: AtomicUsize=AtomicUsize::new(0);
const DUR_ONE_DAY:Duration=Duration::from_secs(86400);
const RETRY_INTERVAL:Duration=Duration::from_secs(1800);
fn has_no_active_conns()->bool { !ACTIVE.load(Ordering::SeqCst) }
fn check_update(_:bool)->Result<(),&'static str> {
 CALLS.fetch_add(1,Ordering::SeqCst);
 if ERROR.load(Ordering::SeqCst) {Err("offline")}else{Ok(())}
}
fn tested()->Duration {
"""+body+r"""check_interval }
fn main(){
 assert_eq!(tested(),RETRY_INTERVAL);
 ERROR.store(true,Ordering::SeqCst); assert_eq!(tested(),RETRY_INTERVAL);
 let before=CALLS.load(Ordering::SeqCst);
 ACTIVE.store(true,Ordering::SeqCst); assert_eq!(tested(),RETRY_INTERVAL);
 assert_eq!(CALLS.load(Ordering::SeqCst),before+1);
}
"""
            path=root/'retry_test.rs'; path.write_text(harness,encoding='utf-8')
            binary=root/'retry-test'
            subprocess.run(['rustc','--edition=2021',str(path),'-o',str(binary)],check=True,capture_output=True,timeout=60)
            subprocess.run([str(binary)],check=True,capture_output=True,timeout=30)

    @unittest.skipIf(sys.platform == 'win32', 'Apache publication uses Linux file locking')
    def test_publication_is_monotonic_and_rejects_corrupt_files(self):
        from deploy import deploy
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prepare(self.source(root), root / 'bundle', 'StatusDesk', '1.5.0', '123', 'abc')
            deploy(root / 'bundle', root / 'public', public_download=True)
            channel = root / 'public/channels/statusdesk/test/windows-x64.json'
            previous = channel.read_bytes()
            catalog = json.loads((root / 'public/downloads.json').read_text())
            url = catalog['items']['windows-x64']['url']
            self.assertTrue(url.endswith('/windows-x64/2/client-windows-x64.exe'))
            public_file = root / 'public' / url.removeprefix('/client/')
            self.assertEqual(public_file.read_bytes(), (root / 'input/client.exe').read_bytes())
            deploy(root / 'bundle', root / 'public')
            metadata = root / 'bundle/channels/statusdesk/test/windows-x64.json'
            changed = json.loads(metadata.read_text())
            changed['version'] = '1.5.0.1'
            metadata.write_text(json.dumps(changed))
            with self.assertRaises(ValueError):
                deploy(root / 'bundle', root / 'public')
            metadata.write_bytes(previous)
            (root / 'bundle/releases/statusdesk/test/windows-x64/2/client-windows-x64.exe').write_bytes(b'corrupted')
            with self.assertRaises(ValueError):
                deploy(root / 'bundle', root / 'public')
            self.assertEqual(previous, channel.read_bytes())

    @unittest.skipIf(sys.platform == 'win32', 'Apache publication uses Linux file locking')
    def test_new_upstream_base_replaces_channel_and_download_with_same_binary(self):
        from deploy import deploy
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self.source(root)
            receipt_path = source / 'stdesk-update-build.json'
            for version, revision in (('1.5.0.3', 281496451547139), ('1.5.1.1', 281496451612673)):
                receipt = json.loads(receipt_path.read_text())
                receipt.update(version=version, revision=revision)
                receipt_path.write_text(json.dumps(receipt))
                bundle = root / version
                prepare(source, bundle, 'StatusDesk', version, '123', 'abc')
                deploy(bundle, root / 'public', public_download=True)
            channel = load_manifest((root/'public/channels/statusdesk/test/windows-x64.json').read_bytes())
            catalog = json.loads((root/'public/downloads.json').read_text())['items']['windows-x64']
            self.assertEqual(channel['version'], '1.5.1.1')
            self.assertEqual(catalog['version'], channel['version'])
            self.assertIn('/'+str(channel['revision'])+'/', catalog['url'])
            self.assertEqual((root/'public'/catalog['url'].removeprefix('/client/')).read_bytes(), (source/'client.exe').read_bytes())

    @unittest.skipIf(sys.platform == 'win32', 'Apache publication uses Linux file locking')
    def test_x86_and_x64_same_revision_use_separate_files_and_channels(self):
        from deploy import deploy
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self.source(root)
            prepare(source, root / 'bundle64', 'StatusDesk', '1.5.0', '123', 'abc')
            deploy(root / 'bundle64', root / 'public', public_download=True)
            receipt_path = source / 'stdesk-update-build.json'
            receipt = json.loads(receipt_path.read_text())
            receipt['platform'] = 'windows-x86'
            receipt_path.write_text(json.dumps(receipt))
            binary = bytearray((source / 'client.exe').read_bytes())
            binary[132:134] = b'\x4c\x01'
            (source / 'client.exe').write_bytes(binary)
            prepare(source, root / 'bundle32', 'StatusDesk', '1.5.0', '124', 'abc')
            deploy(root / 'bundle32', root / 'public', public_download=True)
            catalog = json.loads((root / 'public/downloads.json').read_text())
            self.assertEqual(set(catalog['items']), {'windows-x64','windows-x86'})
            for platform in ('windows-x64','windows-x86'):
                channel = load_manifest((root / 'public/channels/statusdesk/test' / (platform + '.json')).read_bytes())
                file = root / 'public' / catalog['items'][platform]['url'].removeprefix('/client/')
                self.assertEqual(channel['platform'], platform)
                self.assertEqual(channel['filename'], file.name)


if __name__ == '__main__':
    unittest.main()
