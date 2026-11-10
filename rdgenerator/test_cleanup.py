import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from django.test import Client, SimpleTestCase, override_settings
from .cleanup import local_cleanup
from .build_downloads import library
from updates.cleanup import server_plan, remove, safe_file


@override_settings(LOCAL_GITHUB_BUILD=True, SH_SECRET='unused', ALLOWED_HOSTS=['testserver'])
class CleanupTests(SimpleTestCase):
    def test_local_preserves_latest_per_platform_format_and_channel_and_prevents_redownload(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)):
            root = Path(directory)/'downloads'
            for name, platform, version, extension, channel in [
                ('old','windows-x64','1.5.1.9','.exe','stable'),
                ('new','windows-x64','1.5.1.10','.exe','stable'),
                ('32','windows-x86','1.5.0.3','.exe','stable'),
                ('test','windows-x64','1.5.1.1','.exe','test'),
                ('deb','linux-x64','1.5.1.10','.deb','stable'),
                ('app','linux-x64','1.5.1.9','.AppImage','stable')]:
                folder=root/name;folder.mkdir(parents=True)
                filename=name+extension
                (folder/filename).write_bytes(b'installer')
                entry=dict(id=name,relative_path=name+'/'+filename,filename=filename,platform=platform,
                           version=version,receipt={'product':'statusdesk','channel':channel})
                (folder/'library.json').write_text(json.dumps([entry]),encoding='utf-8')
            preview=local_cleanup()
            self.assertEqual([i['path'] for i in preview['items']],['old/old.exe'])
            with self.assertRaises(ValueError): local_cleanup('unconfirmed')
            self.assertTrue((root/'old/old.exe').exists())
            result=local_cleanup(preview['token'])
            self.assertEqual(result['deleted'],1)
            self.assertEqual(json.loads((root/'old/library.json').read_text()),[])
            self.assertEqual({e['id'] for e in library()},{'new','32','test','deb','app'})
            self.assertEqual(local_cleanup()['items'],[])

    def test_server_keeps_downloads_and_all_channels_and_rejects_changed_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            old='downloads/StatusDesk-linux-x64-'+'a'*16+'.deb'
            current='downloads/StatusDesk-linux-x64-'+'b'*16+'.deb'
            stable='releases/statusdesk/stable/windows-x64/12/client-windows-x64.exe'
            test='releases/statusdesk/test/windows-x64/13/client-windows-x64.exe'
            for name in (old,current,stable,test,'index.html'):
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'file')
            catalog={'schema':1,'items':{'linux-x64':{'url':'/client/'+current,'version':'1.5.1.2'}}}
            (root/'downloads.json').write_text(json.dumps(catalog))
            for channel, revision in [('stable',12),('test',13)]:
                path=root/f'channels/statusdesk/{channel}/windows-x64.json';path.parent.mkdir(parents=True)
                path.write_text(json.dumps(dict(product='statusdesk',channel=channel,platform='windows-x64',revision=revision,filename='client-windows-x64.exe')))
            preview=server_plan(root)
            self.assertEqual([i['path'] for i in preview['items']],[old])
            # A new publication between preview and confirmation must cancel deletion.
            catalog['items']['linux-x64']['url']='/client/'+old
            (root/'downloads.json').write_text(json.dumps(catalog))
            with self.assertRaises(ValueError): remove(root,server_plan(root),preview['token'])
            self.assertTrue((root/old).exists())
            (root/'downloads.json').write_text('{broken')
            with self.assertRaises(ValueError): server_plan(root)
            with self.assertRaises(ValueError): safe_file(root,'../outside')

    def test_cleanup_endpoints_require_loopback_csrf_and_preview_confirmation(self):
        client=Client()
        self.assertEqual(client.get('/desktop/cleanup',REMOTE_ADDR='127.0.0.1').status_code,405)
        self.assertEqual(client.post('/desktop/cleanup',data='{}',content_type='application/json',REMOTE_ADDR='10.0.0.1').status_code,403)
        self.assertEqual(Client(enforce_csrf_checks=True).post('/desktop/cleanup',data='{}',content_type='application/json',REMOTE_ADDR='127.0.0.1').status_code,403)
        with patch('rdgenerator.cleanup.server_cleanup',return_value={'items':[],'bytes':0,'token':'a'*64}) as remote:
            response=client.post('/desktop/cleanup',data=json.dumps({'scope':'server','action':'preview'}),content_type='application/json',REMOTE_ADDR='127.0.0.1')
            self.assertEqual(response.status_code,200)
            remote.assert_called_once_with(None)
            response=client.post('/desktop/cleanup',data=json.dumps({'scope':'server','action':'delete'}),content_type='application/json',REMOTE_ADDR='127.0.0.1')
            self.assertEqual(response.status_code,400)
