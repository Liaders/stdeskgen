import json
import base64
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from sciter_compat import apply


class SciterCompatibilityTests(unittest.TestCase):
    def original(self,name):
        source=Path(__file__).resolve().parents[2]/'rustdesk'
        return subprocess.check_output(['git','-c',f'safe.directory={source.as_posix()}','-C',str(source),'show',os.environ.get('RUSTDESK_TEST_REF','HEAD')+':'+name])

    def test_windows_icon_uses_supplied_png_and_macos_branch_stays_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'src/ui').mkdir(parents=True)
            for name in ('src/ui.rs','src/ui/index.tis'):(root/name).write_bytes(self.original(name))
            before=(root/'src/ui.rs').read_text(encoding='utf-8')
            apply(root,'https://api.example.test',True)
            after=(root/'src/ui.rs').read_text(encoding='utf-8')
            marker='#[cfg(not(target_os = "macos"))] // 128x128 no padding'
            self.assertEqual(before.split(marker)[0],after.split(marker)[0])
            self.assertIn('include_bytes!("../res/icon.png")',after.split(marker)[1])
            self.assertFalse(any(ord(c)<32 and c not in '\n\r\t' for c in after))

    def test_supplied_logo_is_embedded_above_your_desktop(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'src/ui').mkdir(parents=True)
            for name in ('src/ui/index.tis','src/ui/index.css'):(root/name).write_bytes(self.original(name))
            logo=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+afo0AAAAASUVORK5CYII=')
            apply(root,'',logo=logo)
            page=(root/'src/ui/index.tis').read_text(encoding='utf-8')
            self.assertLess(page.index('<div #rdgen-client-logo'),page.index("translate('Your Desktop')"))
            self.assertIn(base64.b64encode(logo).decode(),(root/'src/ui/index.css').read_text(encoding='utf-8'))
            self.assertNotIn('rdgenVerifyCurrentUser',page)

    def test_current_user_without_pro_verifier_loads_address_book_only_for_configured_api(self):
        node=shutil.which('node')
        if not node:self.skipTest('Node.js is required for account response regression test')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'src/ui').mkdir(parents=True)
            (root/'src/ui/index.tis').write_bytes(self.original('src/ui/index.tis'))
            apply(root,'https://api.example.test')
            source=(root/'src/ui/index.tis').read_text(encoding='utf-8')
            functions=source.split('function rdgenVerifyCurrentUser',1)[1].split('function getHttpHeaders()',1)[0]
            functions=('function rdgenVerifyCurrentUser'+functions).replace('#post',"'post'")
            test=root/'test.cjs'
            test.write_text(functions+'''
const assert=require('assert');
let token='test-token',api='https://api.example.test',response,bookCalls=0,error='',signatureCalls=0;
const handler={get_local_option:()=>token,get_api_server:()=>api,verify_login:(value)=>{signatureCalls++;if(typeof value!=='string')throw Error('invalid Sciter argument');return value==='valid';},get_uuid:()=>''};
const app={update(){}},myIdMenu={update(){}},my_id='';
let abLoading,abError;
function getHttpHeaders(){return 'Authorization: Bearer '+token;}
function set_local_user_info(){}
function getAb(){bookCalls++;}
function handleAbError(value){error=value;}
function reset_token(){token='';}
function httpRequest(url,method,body,success,failure){try{success(response);}catch(e){failure(JSON.stringify(response),0);}}
response={name:'ainur',display_name:'Ай нур',email:'',status:1,is_admin:false,info:{}};
refreshCurrentUser();assert.equal(bookCalls,1);assert.equal(error,'');assert.equal(signatureCalls,0);
response={...response,verifier:'invalid'};refreshCurrentUser();assert.equal(bookCalls,1);assert.equal(signatureCalls,1);
response={...response,verifier:'valid'};refreshCurrentUser();assert.equal(bookCalls,2);
delete response.verifier;api='https://different.example.test';refreshCurrentUser();assert.equal(bookCalls,2);
api='https://api.example.test';response={name:''};refreshCurrentUser();assert.equal(bookCalls,2);
response={error:'Invalid token'};refreshCurrentUser();assert.equal(token,'');assert.equal(bookCalls,2);
console.log('CortenDesk user response, verifier validation, API binding and invalid token OK');
''',encoding='utf-8')
            result=subprocess.run([node,str(test)],capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(result.returncode,0,result.stderr)
