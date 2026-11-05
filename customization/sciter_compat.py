"""Local Sciter fixes: window icon and authenticated CortenDesk currentUser format."""
import argparse
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit


def apply(root, api, icon=False):
    edits={}
    parsed=urlsplit(api)
    if parsed.scheme=='https' and parsed.hostname and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment:
        path=root/'src/ui/index.tis'
        source=path.read_text(encoding='utf-8')
        anchor='if (!handler.verify_login(data.verifier, token)) {'
        if source.count(anchor)!=1 or 'function rdgenVerifyCurrentUser' in source:
            raise ValueError('Incompatible Sciter currentUser handler')
        helper=Path(__file__).with_name('sciter_current_user.tis').read_text(encoding='utf-8').replace('@API@',json.dumps(api.rstrip('/')))
        edits[path]=source.replace('function refreshCurrentUser() {',helper+'\nfunction refreshCurrentUser() {',1).replace(anchor,'if (!rdgenVerifyCurrentUser(data, token)) {',1)
    if icon:
        path=root/'src/ui.rs'
        source=path.read_text(encoding='utf-8')
        start=source.index('pub fn get_icon() -> String {')
        end=source.index('\n}',start)+2
        function=source[start:end]
        pattern=r'(#\[cfg\(not\(target_os = "macos"\)\)\][^\n]*\n    \{)\n.*?\n    \}'
        replacement=r'''\1
        let bytes = include_bytes!("../res/icon.png");
        let encoded = hbb_common::sodiumoxide::base64::encode(
            bytes, hbb_common::sodiumoxide::base64::Variant::Original);
        format!("data:image/png;base64,{encoded}")
    }'''
        function,count=re.subn(pattern,replacement,function,flags=re.S)
        if count!=1: raise ValueError('Incompatible Sciter Windows icon function')
        edits[path]=source[:start]+function+source[end:]
    for path,source in edits.items():path.write_text(source,encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,default=Path('.'))
    args=parser.parse_args()
    apply(args.source,os.environ.get('apiServer',''),os.environ.get('iconlink_url','false')!='false')
