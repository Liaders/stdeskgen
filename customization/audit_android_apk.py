"""Validate the built APK layout and collect unsigned files for local signing."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile


def audit(root,abi):
    folder=root/'flutter/build/app/outputs/flutter-apk'
    files=list(folder.glob('app-'+abi+'-release*.apk'))
    if len(files)!=1:raise ValueError('Expected one APK for '+abi)
    path=files[0]
    metadata=json.loads((root/'stdesk-android-build.json').read_text(encoding='utf-8'))
    with zipfile.ZipFile(path) as archive:
        if archive.testzip():raise ValueError('Corrupt APK archive')
        if 'lib/'+abi+'/librustdesk.so' not in archive.namelist():raise ValueError('Missing native RustDesk library')
        for field,name in [('icon_sha256','icon.png'),('logo_sha256','logo.png')]:
            if metadata[field] and hashlib.sha256(archive.read('assets/flutter_assets/assets/'+name)).hexdigest()!=metadata[field]:
                raise ValueError('APK branding mismatch: '+name)
    sdk=Path(os.environ['ANDROID_HOME'])/'build-tools/36.0.0'
    badging=subprocess.check_output([str(sdk/'aapt'),'dump','badging',str(path)],text=True)
    if "name='"+metadata['package']+"'" not in badging or "versionName='"+metadata['version']+"'" not in badging or "versionCode='"+str(metadata['version_code'])+"'" not in badging:
        raise ValueError('APK package/version mismatch')
    output=root/'android-output';output.mkdir(exist_ok=True)
    target=output/(os.environ['filename']+'-'+abi+'-unsigned.apk')
    shutil.copyfile(path,target)
    metadata['abi']=abi
    (output/'stdesk-android-build.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    print('APK package, version, architecture and branding verified. Local signing required.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,default=Path('.'));args=parser.parse_args()
    audit(args.source,os.environ['STDESK_ANDROID_ABI'])
