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
        names=['src/ui_interface.rs','src/platform/windows.rs','build.py','flutter/pubspec.yaml','flutter/windows/runner/Runner.rc','build.rs','libs/portable/build.rs','Cargo.toml','libs/hbb_common/src/config.rs','src/common.rs','flutter/android/app/src/main/kotlin/com/carriez/flutter_hbb/MainService.kt','flutter/lib/models/native_model.dart','flutter/android/app/build.gradle','flutter/android/gradle.properties','flutter/android/app/src/main/AndroidManifest.xml','flutter/android/app/src/main/res/values/ic_launcher_background.xml']
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name in names:
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(self.original(name))
            assets=root/'input';assets.mkdir();png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+afo0AAAAASUVORK5CYII=')
            for name in ('icon.png','logo.png'):(assets/name).write_bytes(png)
            metadata=apply(root,inputs,assets)
            self.assertEqual((root/'Cargo.toml').read_bytes(),cargo)
            self.assertEqual(metadata['package'],'ru.status16.statusdesk')
            self.assertFalse((root/'flutter/android/app/src/main/res/values/ic_launcher_background.xml').exists())
            self.assertIn(inputs['custom'],(root/'flutter/lib/models/native_model.dart').read_text(encoding='utf-8'))
            self.assertIn(inputs['custom'],(root/'flutter/android/app/src/main/kotlin/com/carriez/flutter_hbb/MainService.kt').read_text(encoding='utf-8'))
            self.assertIn('signingConfig null',(root/'flutter/android/app/build.gradle').read_text())
            self.assertIn('org.gradle.jvmargs=-Xmx4g',(root/'flutter/android/gradle.properties').read_text())
            self.assertEqual(metadata['logo_sha256'],hashlib.sha256(png).hexdigest())
            self.assertTrue(verify(root,inputs,'android',assets))

    def test_android_version_code_increases_across_upstream_bases(self):
        self.assertLess(android_version_code('1.5.0','1.5.0.65535'),android_version_code('1.5.1','1.5.1.1'))
        self.assertEqual(android_version_code('1.5.0','1.5.0.3'),688128003)
