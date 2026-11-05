"""Validate the built APK layout and collect unsigned files for local signing."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import zipfile


def audit(root,abi):
    folder=root/'flutter/build/app/outputs/flutter-apk'
    files=list(folder.glob('app-'+abi+'-release*.apk'))+list(folder.glob('app-release*.apk'))
    if len(files)!=1:raise ValueError('Expected one APK for '+abi)
    path=files[0]
    metadata=json.loads((root/'stdesk-android-build.json').read_text(encoding='utf-8'))
    with zipfile.ZipFile(path) as archive:
        if archive.testzip():raise ValueError('Corrupt APK archive')
        native_abis={name.split('/')[1] for name in archive.namelist() if name.startswith('lib/') and name.endswith('/librustdesk.so')}
        if native_abis!={abi}:raise ValueError('APK native architecture mismatch: '+str(sorted(native_abis)))
        for field,name in [('icon_sha256','icon.png'),('logo_sha256','logo.png')]:
            if metadata[field] and hashlib.sha256(archive.read('assets/flutter_assets/assets/'+name)).hexdigest()!=metadata[field]:
                raise ValueError('APK branding mismatch: '+name)
    sdk=Path(os.environ['ANDROID_HOME'])/'build-tools/36.0.0'
    badging=subprocess.check_output([str(sdk/'aapt'),'dump','badging',str(path)],text=True)
    package_line=next((line for line in badging.splitlines() if line.startswith('package:')), '')
    actual=dict(re.findall(r"(\w+)='([^']*)'",package_line))
    expected={'name':metadata['package'],'versionName':metadata['version'],'versionCode':str(metadata['version_code'])}
    observed={key:actual.get(key) for key in expected}
    if observed!=expected:
        raise ValueError('APK package/version mismatch: expected '+json.dumps(expected)+', got '+json.dumps(observed))
    output=root/'android-output';output.mkdir(exist_ok=True)
    target=output/(os.environ['filename']+'-'+abi+'-unsigned.apk')
    shutil.copyfile(path,target)
    metadata['abi']=abi
    (output/'stdesk-android-build.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    print('APK package, version, architecture and branding verified. Local signing required.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,default=Path('.'));args=parser.parse_args()
    audit(args.source,os.environ['STDESK_ANDROID_ABI'])
