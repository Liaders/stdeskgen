"""Sign downloaded Android APKs locally with a stable platform-required application key."""
import base64
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import secrets
import re
import subprocess
from django.conf import settings
from .android_tools import ensure_tools


class _Blob(ctypes.Structure):
    _fields_=[('cbData',wintypes.DWORD),('pbData',ctypes.POINTER(ctypes.c_ubyte))]


def _dpapi(data,protect):
    if os.name!='nt':raise OSError('Local Android signing is configured for Windows')
    buffer=ctypes.create_string_buffer(data)
    source=_Blob(len(data),ctypes.cast(buffer,ctypes.POINTER(ctypes.c_ubyte)));output=_Blob()
    dll=ctypes.WinDLL('crypt32',use_last_error=True)
    if protect:ok=dll.CryptProtectData(ctypes.byref(source),None,None,None,None,1,ctypes.byref(output))
    else:ok=dll.CryptUnprotectData(ctypes.byref(source),None,None,None,None,1,ctypes.byref(output))
    if not ok:raise ctypes.WinError(ctypes.get_last_error())
    kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.LocalFree.argtypes=[ctypes.c_void_p]
    try:return ctypes.string_at(output.pbData,output.cbData)
    finally:kernel.LocalFree(output.pbData)


def _run(command,env=None,cwd=None):
    result=subprocess.run(command,capture_output=True,env=env,cwd=cwd,timeout=300,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:raise ValueError('Android signing tool failed: '+result.stderr.decode('utf-8','replace')[-2500:])
    return result.stdout


def _identity(tools):
    root=Path(settings.BASE_DIR)/'.local-android-signing';root.mkdir(exist_ok=True)
    config=root/'identity.json';store=root/'statusdesk.p12'
    if config.exists():
        data=json.loads(config.read_text(encoding='utf-8'))
        if not store.is_file():raise ValueError('Android signing key is missing; restore it from backup')
        password=_dpapi(base64.b64decode(data['password_dpapi']),False).decode()
    elif store.exists():raise ValueError('Android key exists without its identity metadata; restore the matching backup')
    else:
        password=secrets.token_urlsafe(48)
        env={**os.environ,'STDESK_ANDROID_PASSWORD':password}
        _run([tools['keytool'],'-genkeypair','-noprompt','-keystore',str(store),'-storetype','PKCS12','-alias','statusdesk','-keyalg','RSA','-keysize','3072','-validity','10000','-dname','CN=StatusDesk','-storepass:env','STDESK_ANDROID_PASSWORD'],env)
        data={'alias':'statusdesk','password_dpapi':base64.b64encode(_dpapi(password.encode(),True)).decode()}
        certificate=_run([tools['keytool'],'-exportcert','-keystore',str(store),'-alias','statusdesk','-storepass:env','STDESK_ANDROID_PASSWORD'],env)
        data['certificate_sha256']=hashlib.sha256(certificate).hexdigest()
        config.write_text(json.dumps(data,indent=2),encoding='utf-8');config.chmod(0o600)
    return store,password,data


def sign_apk(path,metadata):
    tools=ensure_tools();store,password,identity=_identity(tools)
    if metadata.get('schema')!=1 or metadata.get('platform')!='android' or not re.fullmatch(r'[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*){2,}',metadata.get('package','')):
        raise ValueError('Missing trusted StatusDesk Android build metadata')
    badging=_run([tools['aapt'],'dump','badging',path.name],cwd=path.parent).decode('utf-8','replace')
    for key,value in [('name',metadata['package']),('versionName',metadata['version']),('versionCode',str(metadata['version_code']))]:
        if key+"='"+value+"'" not in badging:raise ValueError('Downloaded APK package or version does not match its build metadata')
    aligned=path.with_name('.aligned.apk');temporary=path.with_name('.signed.apk');target=path.with_name(path.name.replace('-unsigned.apk','.apk'))
    env={**os.environ,'STDESK_ANDROID_PASSWORD':password}
    try:
        _run([tools['zipalign'],'-P','16','-f','4',path.name,aligned.name],cwd=path.parent)
        _run([tools['java'],'-jar',tools['signer'],'sign','--ks',str(store),'--ks-key-alias',identity['alias'],'--ks-pass','env:STDESK_ANDROID_PASSWORD','--key-pass','env:STDESK_ANDROID_PASSWORD','--v1-signing-enabled','true','--v2-signing-enabled','true','--v3-signing-enabled','true','--v4-signing-enabled','false','--out',str(temporary),str(aligned)],env)
        verified=_run([tools['java'],'-jar',tools['signer'],'verify','--verbose','--print-certs',str(temporary)]).decode('utf-8','replace')
        if identity['certificate_sha256'].lower() not in verified.lower():raise ValueError('APK signing certificate mismatch')
        temporary.replace(target)
    finally:
        aligned.unlink(missing_ok=True);temporary.unlink(missing_ok=True)
    metadata={**metadata,'signing':'signed-locally','certificate_sha256':identity['certificate_sha256']}
    (path.parent/'stdesk-android-build.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    return target,metadata


def export_backup(target):
    """Operator-invoked offline backup; the password is written to a file, never printed."""
    import zipfile
    tools=ensure_tools();store,password,identity=_identity(tools)
    with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(store,'statusdesk.p12')
        archive.writestr('password.txt',password)
        archive.writestr('identity-public.json',json.dumps({'alias':identity['alias'],'certificate_sha256':identity['certificate_sha256']},indent=2))
        archive.writestr('README.txt','Keep this offline backup private. The APK signing key and password are required to update existing Android installations.')


def restore_backup(source):
    import zipfile
    tools=ensure_tools()
    root=Path(settings.BASE_DIR)/'.local-android-signing';root.mkdir(exist_ok=True)
    with zipfile.ZipFile(source) as archive:
        store=archive.read('statusdesk.p12');password=archive.read('password.txt').decode()
        public=json.loads(archive.read('identity-public.json'))
    target=root/'statusdesk.p12'
    if target.exists() and target.read_bytes()!=store:raise ValueError('A different Android key already exists; it will not be overwritten')
    temporary=root/'restore.p12';temporary.write_bytes(store)
    try:
        certificate=_run([tools['keytool'],'-exportcert','-keystore',str(temporary),'-alias',public['alias'],'-storepass:env','STDESK_ANDROID_PASSWORD'],{**os.environ,'STDESK_ANDROID_PASSWORD':password})
        if hashlib.sha256(certificate).hexdigest()!=public['certificate_sha256']:raise ValueError('Android backup certificate mismatch')
        temporary.replace(target)
        data={**public,'password_dpapi':base64.b64encode(_dpapi(password.encode(),True)).decode()}
        (root/'identity.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    finally:temporary.unlink(missing_ok=True)


if __name__=='__main__':
    import argparse
    os.environ.setdefault('DJANGO_SETTINGS_MODULE','rdgen.settings')
    import django
    django.setup()
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('backup','restore'));parser.add_argument('file',type=Path)
    args=parser.parse_args()
    if args.action=='backup':export_backup(args.file)
    else:restore_backup(args.file)
    print('Android signing identity '+args.action+' completed. Keep the backup private.')
