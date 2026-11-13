import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from prepare_android import apply, android_version_code
from verify_build_inputs import verify


class AndroidSourceTests(unittest.TestCase):
    def original(self,name):
        source=Path(__file__).resolve().parents[2]/'rustdesk'
        if name=='libs/hbb_common/src/config.rs':
            if (source/name).exists():return (source/name).read_bytes()
            return (Path(__file__).resolve().parents[1]/'.desktop/audit/hbb-config-1.5.0.rs').read_bytes()
        return subprocess.check_output(['git','-c',f'safe.directory={source.as_posix()}','-C',str(source),'show',os.environ.get('RUSTDESK_TEST_REF','HEAD')+':'+name])

    def test_android_embeds_server_service_config_package_and_branding(self):
        inputs={'VERSION':'1.5.0','STDESK_DISPLAY_VERSION':'1.5.0.3','androidappid':'ru.status16.statusdesk','appname':'StatusDesk',
                'server':'id.example.test','serverPort':'21116','key':'test-public-key','apiServer':'https://api.example.test',
                'custom':base64.b64encode(json.dumps({'app-name':'StatusDesk','default-settings':{'access-mode':'custom'}}).encode()).decode(),
                'iconlink_url':'local','logolink_url':'local'}
        ref=os.environ.get('RUSTDESK_TEST_REF','HEAD')
        cargo=self.original('Cargo.toml')
        import re
        inputs['VERSION']=re.search(rb'^version = "([^"]+)"',cargo,re.M)[1].decode()
        inputs['STDESK_DISPLAY_VERSION']=inputs['VERSION']+'.3'
        names=['src/lang/ru.rs','flutter/lib/models/model.dart','src/client.rs','src/client/io_loop.rs','src/ui/common.tis','src/ui_session_interface.rs','src/hbbs_http/sync.rs','src/ui_interface.rs','src/platform/windows.rs','build.py','flutter/pubspec.yaml','flutter/windows/runner/Runner.rc','build.rs','libs/portable/build.rs','Cargo.toml','libs/hbb_common/src/config.rs','src/common.rs','flutter/android/app/src/main/kotlin/com/carriez/flutter_hbb/MainService.kt','flutter/lib/models/native_model.dart','flutter/android/app/build.gradle','flutter/android/gradle.properties','flutter/android/app/src/main/AndroidManifest.xml','flutter/android/app/src/main/res/values/ic_launcher_background.xml']
        names+=['flutter/lib/common/widgets/peer_card.dart','flutter/lib/mobile/pages/connection_page.dart','flutter/lib/mobile/pages/home_page.dart','flutter/lib/common.dart','flutter/lib/mobile/pages/settings_page.dart','flutter/lib/common/widgets/my_group.dart',
                'flutter/lib/models/peer_tab_model.dart','flutter/lib/common/widgets/peer_tab_page.dart','src/lang/ru.rs',
                'flutter/android/app/src/main/res/values/strings.xml',
                'flutter/android/app/src/main/kotlin/com/carriez/flutter_hbb/BootReceiver.kt',
                'flutter/android/app/src/main/kotlin/com/carriez/flutter_hbb/FloatingWindowService.kt']
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name in names:
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(self.original(name))
            assets=root/'input';assets.mkdir();png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+afo0AAAAASUVORK5CYII=')
            for name in ('icon.png','logo.png'):(assets/name).write_bytes(png)
            (assets/'logo_light.png').write_bytes(png+b'light')
            (assets/'logo_dark.png').write_bytes(png+b'dark')
            metadata=apply(root,inputs,assets)
            self.assertEqual((root/'Cargo.toml').read_bytes(),cargo)
            self.assertEqual(metadata['package'],'ru.status16.statusdesk')
            self.assertFalse((root/'flutter/android/app/src/main/res/values/ic_launcher_background.xml').exists())
            self.assertIn(inputs['custom'],(root/'flutter/lib/models/native_model.dart').read_text(encoding='utf-8'))
            self.assertIn(inputs['custom'],(root/'flutter/android/app/src/main/kotlin/com/carriez/flutter_hbb/MainService.kt').read_text(encoding='utf-8'))
            self.assertIn('signingConfig null',(root/'flutter/android/app/build.gradle').read_text())
            self.assertIn('org.gradle.jvmargs=-Xmx4g',(root/'flutter/android/gradle.properties').read_text())
            self.assertEqual(metadata['logo_sha256'],hashlib.sha256(png).hexdigest())
            self.assertEqual(metadata['logo_light_sha256'],hashlib.sha256(png+b'light').hexdigest())
            self.assertEqual(metadata['logo_dark_sha256'],hashlib.sha256(png+b'dark').hexdigest())
            self.assertTrue(verify(root,inputs,'android',assets))
            common=(root/'flutter/lib/common.dart').read_text(encoding='utf-8')
            self.assertIn('accent = Color(0xFFEF7F1A)',common)
            self.assertIn('if (isAndroid || bind.mainGetBuildinOption',common)
            settings=(root/'flutter/lib/mobile/pages/settings_page.dart').read_text(encoding='utf-8')
            self.assertNotIn('rustdesk.com',settings)
            self.assertIn('https://status16.ru/',settings)
            model=(root/'flutter/lib/models/peer_tab_model.dart').read_text(encoding='utf-8')
            self.assertIn("'Accessible devices',\n    'Colleagues',",model)
            self.assertIn('maxTabCount = 6;',model)
            self.assertIn('IconFont.deviceGroupFill,\n    Icons.people,',model)
            page=(root/'flutter/lib/common/widgets/peer_tab_page.dart').read_text(encoding='utf-8')
            self.assertIn('_TabEntry(RdgenColleagues(',page)
            self.assertEqual((root/'flutter/lib/mobile/pages/home_page.dart').read_bytes(),self.original('flutter/lib/mobile/pages/home_page.dart'))
            self.assertFalse((root/'flutter/lib/mobile/pages/rdgen_colleagues_page.dart').exists())
            self.assertIn('backgroundColor: isAndroid ? MyTheme.accent : null',common)
            self.assertIn('foregroundColor: isAndroid ? Colors.white : null',common)
            connection=(root/'flutter/lib/mobile/pages/connection_page.dart').read_text(encoding='utf-8')
            self.assertIn('color: isAndroid ? MyTheme.accent : MyTheme.idColor',connection)
            self.assertEqual(common.split('  static ThemeData darkTheme =',1)[1].split('\n  );',1)[0],
                self.original('flutter/lib/common.dart').decode('utf-8').split('  static ThemeData darkTheme =',1)[1].split('\n  );',1)[0])
            self.assertTrue((root/'flutter/lib/common/widgets/rdgen_colleagues.dart').exists())
            service=(root/'flutter/android/app/src/main/kotlin/com/carriez/flutter_hbb/MainService.kt').read_text(encoding='utf-8')
            self.assertIn('DEFAULT_NOTIFY_TITLE = "StatusDesk"',service)
            self.assertIn('val channelName = "StatusDesk"',service)
            from android_branding import apply_launcher, ICONS
            (root/'flutter/android/app/src/main/res/values/colors.xml').write_text('<resources><color name="primary">#0000ff</color><color name="ic_launcher_background">#ffffff</color></resources>')
            apply_launcher(root)
            self.assertIn('#FFEF7F1A',(root/'flutter/android/app/src/main/res/values/colors.xml').read_text())
            self.assertNotIn('ic_launcher_background',(root/'flutter/android/app/src/main/res/values/colors.xml').read_text())
            self.assertEqual((root/'flutter/android/app/src/main/res/mipmap-xxxhdpi/ic_launcher.png').read_bytes(),(ICONS/'mipmap-xxxhdpi/ic_launcher.png').read_bytes())
            self.assertIn('android:roundIcon=',(root/'flutter/android/app/src/main/AndroidManifest.xml').read_text())


    def test_android_version_code_increases_across_upstream_bases(self):
        self.assertLess(android_version_code('1.5.0','1.5.0.65535'),android_version_code('1.5.1','1.5.1.1'))
        self.assertEqual(android_version_code('1.5.0','1.5.0.3'),688128003)
