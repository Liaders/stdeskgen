"""Verify a locally signed APK before it leaves the operator's computer."""
import json
from pathlib import Path
import re
import subprocess
import zipfile

ABIS={'android-arm64':'arm64-v8a','android-armv7':'armeabi-v7a','android-x64':'x86_64'}


def verify(source, platform, version, metadata_path):
    root=Path(__file__).resolve().parents[1]
    metadata=json.loads(metadata_path.read_text(encoding='utf-8'))
    identity=json.loads((root/'.local-android-signing/identity.json').read_text(encoding='utf-8'))
    if (platform not in ABIS or metadata.get('schema')!=1 or metadata.get('platform')!='android'
            or metadata.get('signing')!='signed-locally' or metadata.get('version')!=version
            or metadata.get('certificate_sha256')!=identity['certificate_sha256']):
        raise ValueError('Choose an APK signed with the existing local StatusDesk key and its original metadata')
    with zipfile.ZipFile(source) as archive:
        abis={n.split('/')[1] for n in archive.namelist() if n.startswith('lib/') and n.endswith('/librustdesk.so')}
        if archive.testzip() or 'AndroidManifest.xml' not in archive.namelist() or abis!={ABIS[platform]}:
            raise ValueError('APK architecture or archive mismatch')
    tools=json.loads((root/'.tools/android/tools.json').read_text(encoding='utf-8'))
    def run(command,cwd=None):
        result=subprocess.run(command,cwd=cwd,capture_output=True,timeout=120)
        if result.returncode:raise ValueError('APK verification failed: '+result.stderr.decode('utf-8','replace')[-1500:])
        return result.stdout.decode('utf-8','replace')
    badging=run([tools['aapt'],'dump','badging',source.name],source.parent)
    line=next((line for line in badging.splitlines() if line.startswith('package:')),'')
    actual=dict(re.findall(r"(\w+)='([^']*)'",line))
    if any(actual.get(k)!=v for k,v in {'name':metadata['package'],'versionName':version,'versionCode':str(metadata['version_code'])}.items()):
        raise ValueError('APK package/version does not match the original metadata')
    verified=run([tools['java'],'-jar',tools['signer'],'verify','--print-certs',str(source)])
    certs=re.findall(r'Signer #\d+ certificate SHA-256 digest: ([0-9a-f]+)',verified,re.I)
    if [c.lower() for c in certs]!=[identity['certificate_sha256'].lower()]:
        raise ValueError('APK signing certificate does not match the existing StatusDesk key')
    return metadata
