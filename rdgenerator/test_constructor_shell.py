from collections import Counter
from html.parser import HTMLParser
import json
from pathlib import Path
import tempfile
from unittest.mock import patch, Mock

from django.test import Client, SimpleTestCase, override_settings
from .forms import GenerateForm


@override_settings(LOCAL_GITHUB_BUILD=True, SH_SECRET='unused', ALLOWED_HOSTS=['testserver'])
class ConstructorShellTests(SimpleTestCase):
    def data(self):
        data={}
        for name,field in GenerateForm().fields.items():
            if field.initial is not None: data[name]='on' if field.initial is True else field.initial
            elif field.required and hasattr(field,'choices'): data[name]=next(iter(field.choices))[0]
        return {**data,'exename':'LegacyDesk','appname':'LegacyDesk','serverIP':'server.example',
                'version':'1.5.1','platform':'windows','build_number':3,'build_scope':'single'}

    def test_new_sections_preserve_every_legacy_field_and_embed_existing_config(self):
        expected=set('android_architecture androidappid apiServer appname autoClose auto_update_enabled batch_auto_update_enabled batch_ui_profile build_number compname defaultManual delayFix denyLan direction downloadLink enableAudio enableBlockingInput enableCamera enableClipboard enableDirectIP enableFileTransfer enableKeyboard enablePrinter enableRecording enableRemoteModi enableRemoteRestart enableTCP enableTerminal exename hidecm iconbase64 iconfile installation key logodarkbase64 logodarkfile logolightbase64 logolightfile overrideManual passApproveMode permanentPassword permissionsDorO permissionsType platform privacybase64 privacyfile removeNewVersionNotif removeWallpaper serverIP serverPort settings theme themeDorO ui_profile updates_config urlLink version xOffline'.split())
        class Fields(HTMLParser):
            def __init__(self): super().__init__();self.names=set();self.ids=[]
            def handle_starttag(self,tag,attrs):
                attrs=dict(attrs)
                if tag in ('input','select','textarea') and attrs.get('name'): self.names.add(attrs['name'])
                if attrs.get('id'): self.ids.append(attrs['id'])
        with tempfile.TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)), patch('rdgenerator.build_monitor.start'):
            legacy={**self.data(),'logobase64':'data:image/png;base64,LEGACY','ui_profile':json.dumps({'schema_version':1,'navigation':'text'})}
            (Path(directory)/'default-config.json').write_text(json.dumps(legacy),encoding='utf-8')
            original=(Path(directory)/'default-config.json').read_bytes()
            page=Client().get('/',REMOTE_ADDR='127.0.0.1')
            parsed=Fields();parsed.feed(page.content.decode())
            self.assertTrue(expected <= parsed.names,expected-parsed.names)
            self.assertTrue(all(count==1 for count in Counter(parsed.ids).values()))
            self.assertContains(page,'data-settings-panel="appearance"')
            self.assertContains(page,'normalizeLogoConfiguration')
            self.assertContains(page,'data:image/png;base64,LEGACY')
            self.assertContains(page,'server.example')
            self.assertEqual((Path(directory)/'default-config.json').read_bytes(),original)

    def test_ajax_builds_reuse_existing_dispatch_and_report_validation_and_partial_errors(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)), patch('rdgenerator.build_monitor.start'), patch('rdgenerator.views.generate_custom_client',return_value={'success':True,'local_build':True,'uuid':'test','app_version':'1.5.1.3'}) as send:
            client=Client();headers={'REMOTE_ADDR':'127.0.0.1','HTTP_X_REQUESTED_WITH':'XMLHttpRequest'}
            response=client.post('/generator',self.data(),**headers)
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json()['app_version'],'1.5.1.3')
            self.assertEqual(send.call_args.args[0]['serverIP'],'server.example')
            invalid={**self.data(),'exename':''}
            self.assertEqual(client.post('/generator',invalid,**headers).status_code,400)
            with patch('rdgenerator.batch_build.build_all',return_value=[{'success':True,'platform':'windows'},{'success':False,'platform':'macos','error':'Unavailable'}]):
                response=client.post('/generator',{**self.data(),'build_scope':'all'},**headers)
                self.assertFalse(response.json()['success'])
                self.assertEqual(len(response.json()['builds']),2)
            self.assertEqual(Client(enforce_csrf_checks=True).post('/generator',self.data(),**headers).status_code,403)

    def test_build_status_and_publication_metadata_are_local_and_do_not_expose_build_secrets(self):
        client=Client()
        self.assertEqual(client.get('/desktop/builds-page',REMOTE_ADDR='10.0.0.1').status_code,403)
        self.assertEqual(client.get('/desktop/published',REMOTE_ADDR='10.0.0.1').status_code,403)
        with patch('rdgenerator.desktop.start'),patch('rdgenerator.desktop.recent_local_builds',return_value=[{'id':'x','app_version':'1.5.1.3','status':'queued','secret':'do-not-expose','branch':'private-branch'}]):
            response=client.get('/desktop/builds',REMOTE_ADDR='127.0.0.1')
            self.assertEqual(response.json()['builds'][0]['app_version'],'1.5.1.3')
            self.assertNotIn(b'do-not-expose',response.content)
        response=Mock();response.json.return_value={'schema':1,'items':{'windows-x64':{'version':'1.5.1.7'}}}
        with patch('requests.get',return_value=response):
            self.assertEqual(client.get('/desktop/published',REMOTE_ADDR='127.0.0.1').json()['versions']['windows-x64'],'1.5.1.7')
