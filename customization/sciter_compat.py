"""Local Sciter fixes: window icon and authenticated CortenDesk currentUser format."""
import argparse
import base64
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit
from desktop_chrome import apply_sciter


def apply(root, api, icon=False, logo=None):
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
    if logo is not None:
        if not logo.startswith(b'\x89PNG\r\n\x1a\n'): raise ValueError('Sciter logo must be PNG')
        path=root/'src/ui/index.tis'
        source=edits.get(path,path.read_text(encoding='utf-8'))
        anchor="""                        <div .title style="flow:horizontal; position:relative; height:1.6em; line-height:1.6em">
                            <span>{translate('Your Desktop')}</span>"""
        if source.count(anchor)!=1 or 'rdgen-client-logo' in source:
            raise ValueError('Incompatible Sciter desktop logo anchor')
        edits[path]=source.replace(anchor,'                        <div #rdgen-client-logo />\n'+anchor,1)
        path=root/'src/ui/index.css'
        source=path.read_text(encoding='utf-8')
        uri='data:image/png;base64,'+base64.b64encode(logo).decode()
        edits[path]=source+'\n#rdgen-client-logo { width:*; height:76dip; margin-bottom:12dip; background-image:url("'+uri+'"); background-size:contain; background-position:center; background-repeat:no-repeat; }\n'
    for path,source in edits.items():path.write_text(source,encoding='utf-8')
    apply_sciter(root)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,default=Path('.'))
    args=parser.parse_args()
    logo=(Path(os.environ['RUNNER_TEMP'])/'rdgen-input/logo.png').read_bytes() if os.environ.get('logolink_url','false')!='false' else None
    apply(args.source,os.environ.get('apiServer',''),os.environ.get('iconlink_url','false')!='false',logo)
