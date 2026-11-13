"""Prepare a mobile APK without applying desktop-only UI patches or exporting signing keys."""
import argparse
import base64
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shutil
import xml.etree.ElementTree as ET
from apply_version import apply as apply_version
from versioning import parts
from android_branding import apply_ui, ICONS
from theme_logos import stage


def android_version_code(base,display):
    major,minor,patch,build=parts(base,display)
    value=((major*100+minor)*100+patch)*65536+build
    if not 1<=value<=2100000000: raise ValueError('Android versionCode exceeds supported range')
    return value


def apply(root,inputs,assets):
    base=inputs['VERSION'];display=inputs['STDESK_DISPLAY_VERSION']
    code=android_version_code(base,display)
    shutil.copyfile(ICONS/'app_icon.png',assets/'icon.png')
    package=inputs.get('androidappid') or 'ru.status16.statusdesk'
    if not re.fullmatch(r'[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*){2,}',package):raise ValueError('Invalid Android application ID')
    if package=='com.carriez.flutter_hbb':raise ValueError('Use a separate StatusDesk package ID, not the original RustDesk ID')
    config=json.loads(base64.b64decode(inputs['custom'],validate=True))
    name=inputs.get('appname') or 'StatusDesk'
    apply_version(root,base,display)
    def change(relative,old,new):
        path=root/relative;source=path.read_text(encoding='utf-8')
        if source.count(old)!=1:raise ValueError('Incompatible Android source: '+relative)
        path.write_text(source.replace(old,new,1),encoding='utf-8')
    path=root/'libs/hbb_common/src/config.rs';source=path.read_text(encoding='utf-8')
    for constant,value in [('RENDEZVOUS_SERVERS','&['+json.dumps(inputs['server'])+']'),('RS_PUB_KEY',json.dumps(inputs['key']))]:
        source,count=re.subn(r'(pub const '+constant+r':[^=]+)= [^;]+;',lambda m:m[1]+'= '+value+';',source,count=1)
        if count!=1:raise ValueError('Missing Android server constant: '+constant)
    for constant,offset in [('RENDEZVOUS_PORT',0),('RELAY_PORT',1),('WS_RENDEZVOUS_PORT',2),('WS_RELAY_PORT',3)]:
        source,count=re.subn(r'(pub const '+constant+r': i32 = )\d+;',lambda m:m[1]+str(int(inputs['serverPort'])+offset)+';',source,count=1)
        if count!=1:raise ValueError('Missing Android server port')
    source,count=re.subn(r'(pub static ref APP_NAME:[^\n]*RwLock::new\()"RustDesk"',lambda m:m[1]+json.dumps(name),source,count=1)
    if count!=1:raise ValueError('Missing Android app-name constant')
    path.write_text(source,encoding='utf-8')
    change('src/common.rs','"https://admin.rustdesk.com".to_owned()',json.dumps(inputs['apiServer'])+'.to_owned()')
    # The APK embeds generator-owned JSON, not a RustDesk Pro signed license file.
    path=root/'src/common.rs';source=path.read_text(encoding='utf-8');start=source.index('pub fn read_custom_client(config: &str) {');key=source.index('    const KEY: &str =',start);end=source.index('    let Ok(mut data) =',key)
    source=source[:key]+source[end:];path.write_text(source,encoding='utf-8')
    kotlin='flutter/android/app/src/main/kotlin/com/carriez/flutter_hbb/MainService.kt'
    path=root/kotlin;source=path.read_text(encoding='utf-8')
    source,count=re.subn(r'FFI\.startServer\(configPath, (homePath, )?""\)',lambda m:'FFI.startServer(configPath, '+(m[1] or '')+json.dumps(inputs['custom'])+')',source,count=1)
    if count!=1:raise ValueError('Missing Android service configuration hook')
    path.write_text(source,encoding='utf-8')
    change('flutter/lib/models/native_model.dart',"customClientConfig: '',",'customClientConfig: '+json.dumps(inputs['custom'])+',')
    change('flutter/android/app/build.gradle','applicationId "com.carriez.flutter_hbb"','applicationId '+json.dumps(package))
    change('flutter/android/app/build.gradle','signingConfig signingConfigs.release','signingConfig null')
    properties=root/'flutter/android/gradle.properties'
    source,count=re.subn(r'(?m)^org\.gradle\.jvmargs=.*$', 'org.gradle.jvmargs=-Xmx4g -XX:MaxMetaspaceSize=1g -XX:+HeapDumpOnOutOfMemoryError',properties.read_text(encoding='utf-8'),count=1)
    if count!=1:raise ValueError('Missing Android Gradle memory configuration')
    properties.write_text(source+'\norg.gradle.workers.max=2\n',encoding='utf-8')
    change('flutter/android/app/src/main/AndroidManifest.xml','android:label="RustDesk"','android:label="'+html.escape(name,quote=True)+'"')
    path=root/'flutter/android/app/src/main/AndroidManifest.xml';source=path.read_text(encoding='utf-8').replace('package="com.carriez.flutter_hbb"','').replace('android:label="RustDesk Input"','android:label="'+html.escape(name,quote=True)+'"');path.write_text(source,encoding='utf-8')
    stage(assets,root/'flutter/assets')
    for filename,targets in [('icon.png',['res/icon.png','flutter/assets/icon.png'])]:
        if (assets/filename).exists():
            for target in targets:
                path=root/target;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(assets/filename,path)
    if (assets/'icon.png').exists():
        # flutter_launcher_icons writes this color into colors.xml itself.
        # RustDesk also ships a separate resource with the same name.
        background=root/'flutter/android/app/src/main/res/values/ic_launcher_background.xml'
        if background.exists():
            tree=ET.parse(background);resources=tree.getroot()
            for item in list(resources):
                if item.tag=='color' and item.get('name')=='ic_launcher_background':resources.remove(item)
            if len(resources):tree.write(background,encoding='utf-8',xml_declaration=True)
            else:background.unlink()
        path=root/'flutter/pubspec.yaml';source=path.read_text(encoding='utf-8').replace('  android: true','  android: true\n  adaptive_icon_background: "#ffffff"\n  adaptive_icon_foreground: "../res/icon.png"\n  adaptive_icon_foreground_inset: 24',1);path.write_text(source,encoding='utf-8')
    # Avoid advertising upstream desktop releases from our Android package.
    change('src/common.rs','pub async fn do_check_software_update() -> hbb_common::ResultType<()> {','pub async fn do_check_software_update() -> hbb_common::ResultType<()> {\n    return Ok(());')
    apply_ui(root,base,name)
    from session_work_groups import apply as apply_work_groups
    apply_work_groups(root, desktop=False)
    record={'schema':1,'platform':'android','package':package,'version':display,'version_code':code,'base_version':base,
            'configuration_sha256':hashlib.sha256(inputs['custom'].encode()).hexdigest(),
            'icon_sha256':hashlib.sha256((assets/'icon.png').read_bytes()).hexdigest() if (assets/'icon.png').exists() else None,
            'logo_sha256':hashlib.sha256((assets/'logo.png').read_bytes()).hexdigest() if (assets/'logo.png').exists() else None,
            **{name.replace('.png','_sha256'):hashlib.sha256((assets/name).read_bytes()).hexdigest() if (assets/name).exists() else None for name in ('logo_light.png','logo_dark.png')},
            'signing':'local-required','accent':'#EF7F1A','colleagues':True}
    (root/'stdesk-android-build.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    return record


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,default=Path('.'));args=parser.parse_args()
    record=apply(args.source,os.environ,Path(os.environ['RUNNER_TEMP'])/'rdgen-input')
    with open(os.environ['GITHUB_ENV'],'a',encoding='utf-8') as output:
        output.write('stdesk_display_version='+record['version']+'\nstdesk_android_version_code='+str(record['version_code'])+'\n')
    print('Android configuration, package ID and branding prepared; values omitted.')
