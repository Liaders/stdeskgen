"""Fail a local build if server defaults or the supplied app icon were not applied."""
import argparse
import base64
import json
import os
from pathlib import Path
import re


def verify(root, expected, platform, assets=None):
    if any(not expected.get(k) for k in ('server','serverPort','key','apiServer')):
        raise ValueError('Missing expected server configuration')
    config=(root/'libs/hbb_common/src/config.rs').read_text(encoding='utf-8')
    common=(root/'src/common.rs').read_text(encoding='utf-8')
    host=re.search(r'pub const RENDEZVOUS_SERVERS:.*?=\s*&(?P<hosts>\[[^;]+\]);',config,re.S)
    key=re.search(r'pub const RS_PUB_KEY:.*?=\s*("[^"\n]*");',config)
    if not host or json.loads(host['hosts']) != [expected['server']]: raise ValueError('ID server default was not applied')
    if not key or json.loads(key[1]) != expected['key']: raise ValueError('Server public key was not applied')
    for name,offset in [('RENDEZVOUS_PORT',0),('RELAY_PORT',1),('WS_RENDEZVOUS_PORT',2),('WS_RELAY_PORT',3)]:
        match=re.search(r'pub const '+name+r': i32 = (\d+);',config)
        if not match or int(match[1]) != int(expected['serverPort'])+offset: raise ValueError('Server port was not applied: '+name)
    if json.dumps(expected['apiServer']) not in common: raise ValueError('API server default was not applied')
    if expected.get('iconlink_url','false') != 'false':
        icon=((assets or root/'.rdgen-input')/'icon.png').read_bytes()
        if (root/'res/icon.png').read_bytes()!=icon: raise ValueError('Supplied application PNG was not applied')
        if platform in ('windows','windows-x86'):
            ico=(root/'res/icon.ico').read_bytes()
            if not ico.startswith(b'\x00\x00\x01\x00'): raise ValueError('Windows ICO resource is invalid')
            if platform=='windows' and (root/'flutter/windows/runner/resources/app_icon.ico').read_bytes()!=ico:
                raise ValueError('Flutter Windows EXE icon differs from supplied application icon')
            if platform=='windows-x86':
                ui=(root/'src/ui.rs').read_text(encoding='utf-8')
                function=ui.split('pub fn get_icon() -> String {',1)[-1].split('\n}',1)[0]
                windows=function.split('#[cfg(not(target_os = "macos"))]',1)[-1]
                if 'include_bytes!("../res/icon.png")' not in windows and base64.b64encode(icon).decode() not in windows:
                    raise ValueError('Sciter window icon was not applied')
        if platform=='macos':
            for name in ('app_icon_16.png','app_icon_32.png','app_icon_64.png','app_icon_128.png','app_icon_256.png','app_icon_512.png','app_icon_1024.png'):
                if not (root/'flutter/macos/Runner/Assets.xcassets/AppIcon.appiconset'/name).is_file():
                    raise ValueError('Missing macOS application icon: '+name)
    if platform=='android':
        for key,name in [('iconlink_url','icon.png'),('logolink_url','logo.png')]:
            if expected.get(key,'false')!='false':
                original=((assets or root/'.rdgen-input')/name).read_bytes()
                if (root/'flutter/assets'/name).read_bytes()!=original:raise ValueError('Android asset was not applied: '+name)
    if platform=='windows-x86' and expected.get('logolink_url','false') != 'false':
        logo=((assets or root/'.rdgen-input')/'logo.png').read_bytes()
        page=(root/'src/ui/index.tis').read_text(encoding='utf-8')
        style=(root/'src/ui/index.css').read_text(encoding='utf-8')
        if '#rdgen-client-logo' not in page or base64.b64encode(logo).decode() not in style:
            raise ValueError('Sciter desktop logo was not applied')
    return True


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,default=Path('.'))
    parser.add_argument('--platform',required=True)
    args=parser.parse_args()
    verify(args.source,{key:os.environ.get(key,'') for key in ('server','serverPort','key','apiServer','iconlink_url','logolink_url')},args.platform,Path(os.environ['RUNNER_TEMP'])/'rdgen-input')
    print('Server defaults and application icon verified (values omitted).')
