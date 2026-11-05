import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from audit_android_apk import audit


class AndroidApkAuditTests(unittest.TestCase):
    def fixture(self, root, extra_abi=False):
        folder=root/'flutter/build/app/outputs/flutter-apk'
        folder.mkdir(parents=True)
        image=b'fixture image bytes'
        with zipfile.ZipFile(folder/'app-release.apk','w') as archive:
            archive.writestr('lib/arm64-v8a/librustdesk.so',b'fixture native library')
            if extra_abi:archive.writestr('lib/armeabi-v7a/librustdesk.so',b'other architecture')
            for name in ('icon.png','logo.png'):
                archive.writestr('assets/flutter_assets/assets/'+name,image)
        metadata={'package':'ru.status16.statusdesk','version':'1.5.1.2','version_code':688193538,
                  'icon_sha256':hashlib.sha256(image).hexdigest(),'logo_sha256':hashlib.sha256(image).hexdigest()}
        (root/'stdesk-android-build.json').write_text(json.dumps(metadata),encoding='utf-8')

    def run_audit(self, root, code=688193538):
        badging=f"package: name='ru.status16.statusdesk' versionCode='{code}' versionName='1.5.1.2'\n"
        with patch.dict(os.environ,{'ANDROID_HOME':str(root/'sdk'),'filename':'StatusDesk-1.5.1.2-android'}),patch('audit_android_apk.subprocess.check_output',return_value=badging):
            audit(root,'arm64-v8a')

    def test_single_architecture_apk_keeps_exact_release_version(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);self.fixture(root);self.run_audit(root)
            self.assertTrue((root/'android-output/StatusDesk-1.5.1.2-android-arm64-v8a-unsigned.apk').is_file())
            self.assertEqual(json.loads((root/'android-output/stdesk-android-build.json').read_text())['version_code'],688193538)

    def test_flutter_split_version_offset_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);self.fixture(root)
            with self.assertRaisesRegex(ValueError,'688195538'):self.run_audit(root,688195538)
            self.assertFalse((root/'android-output').exists())

    def test_unexpected_native_architecture_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);self.fixture(root,extra_abi=True)
            with self.assertRaisesRegex(ValueError,'architecture mismatch'):self.run_audit(root)
