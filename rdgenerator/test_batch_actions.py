import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from django.http import JsonResponse
from django.test import Client, SimpleTestCase, override_settings
from .forms import GenerateForm
from .local_build import LocalBuildError
from .publication_selection import latest_installers


@override_settings(LOCAL_GITHUB_BUILD=True, SH_SECRET='unused', ALLOWED_HOSTS=['testserver'])
class BatchActionTests(SimpleTestCase):
    def form_data(self):
        data={}
        for name,field in GenerateForm().fields.items():
            if field.initial is not None: data[name]='on' if field.initial is True else field.initial
            elif field.required and hasattr(field,'choices'): data[name]=next(iter(field.choices))[0]
        return {**data,'exename':'Test','version':'1.5.0','build_number':3,'platform':'windows-x86',
                'build_scope':'all','batch_auto_update_enabled':'on',
                'batch_ui_profile':json.dumps({'schema_version':1,'colleagues':True})}

    def test_batch_dispatches_same_release_with_android_and_continues_after_failure(self):
        def dispatch(*args,**kwargs):
            if kwargs['platform']=='linux': raise LocalBuildError('Test dispatch failure')
            return {'success':True,'local_build':True,'uuid':'test','filename':'Test'}
        with tempfile.TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)), patch('rdgenerator.build_monitor.start'), patch('rdgenerator.views.dispatch_local',side_effect=dispatch) as send:
            page=Client().post('/',self.form_data(),REMOTE_ADDR='127.0.0.1')
            self.assertEqual(page.status_code,200)
            self.assertContains(page,'Test dispatch failure')
            self.assertEqual([c.kwargs['platform'] for c in send.call_args_list],['windows','windows-x86','linux','macos','android'])
            self.assertTrue(all(c.args[3]=='1.5.0.3' for c in send.call_args_list))
            for call in send.call_args_list:
                self.assertEqual('ui_profile_b64' in call.args[0],call.kwargs['platform'] not in ('windows-x86','android'))
                self.assertEqual('stdesk_update_b64' in call.args[0],call.kwargs['platform'] in ('windows','windows-x86'))

    def test_android_is_available_and_routes_to_local_build(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)), patch('rdgenerator.build_monitor.start'), patch('rdgenerator.views.dispatch_local',return_value={'success':True,'local_build':True,'uuid':'test','filename':'Test'}) as send:
            page=Client().get('/',REMOTE_ADDR='127.0.0.1')
            self.assertContains(page,'<option value="android">')
            self.assertLess(page.content.index(b'id="build-single"'),page.content.index(b'id="id_version"'))
            data=self.form_data();data.update(platform='android',build_scope='single',ui_profile='')
            page=Client().post('/',data,REMOTE_ADDR='127.0.0.1')
            self.assertTrue(send.called)
            self.assertEqual(send.call_args.kwargs['platform'],'android')
            self.assertEqual(send.call_args.args[0]['androidappid'],'ru.status16.statusdesk')

    def test_latest_plan_uses_numeric_versions_separate_platforms_and_excludes_test_channels(self):
        def item(id,platform,version,filename,receipt=None):
            return dict(id=id,platform=platform,version=version,filename=filename,run_id=10,receipt=receipt)
        items=[item('old','windows-x64','1.5.0.9','old.exe'),item('new','windows-x64','1.5.0.10','new.exe'),
               item('test','windows-x64','1.5.0.99','test.exe',{'product':'statusdesk-ci','channel':'test'}),
               item('32','windows-x86','1.5.0.10','32.exe'),item('app','linux-x64','1.5.0.10','linux.AppImage'),
               item('deb','linux-x64','1.5.0.10','linux.deb')]
        self.assertEqual([i['id'] for i in latest_installers(items)],['new','32','deb'])
        with patch('rdgenerator.desktop.library',return_value=items),patch('rdgenerator.desktop._publication_job',side_effect=lambda id,**kw:(id,kw)),patch('rdgenerator.desktop._start_publications',return_value=JsonResponse({'ok':True})) as publish:
            client=Client()
            plan=client.get('/desktop/publication-plan',REMOTE_ADDR='127.0.0.1').json()['items']
            response=client.post('/desktop/publish-latest',data=json.dumps({'ids':[i['id'] for i in plan]}),content_type='application/json',REMOTE_ADDR='127.0.0.1')
            self.assertEqual(response.status_code,200)
            self.assertEqual(len(publish.call_args.args[0]),3)
            publish.reset_mock()
            response=client.post('/desktop/publish-latest',data=json.dumps({'ids':['old']}),content_type='application/json',REMOTE_ADDR='127.0.0.1')
            self.assertEqual(response.status_code,409)
            publish.assert_not_called()
            self.assertEqual(client.get('/desktop/publication-plan',REMOTE_ADDR='10.0.0.1').status_code,403)
            self.assertEqual(Client(enforce_csrf_checks=True).post('/desktop/publish-latest',data='{}',content_type='application/json',REMOTE_ADDR='127.0.0.1').status_code,403)

    def test_publication_continues_after_one_failure_and_reports_each_result(self):
        from . import desktop
        from types import SimpleNamespace
        jobs=[({'platform':'windows-x64'},Path('one.exe'),'1.5.0.3',False),({'platform':'linux-x64'},Path('two.deb'),'1.5.0.3',False)]
        with patch.dict(desktop._task,{'state':'idle','message':''}),patch('rdgenerator.desktop.threading.Thread') as thread,patch('rdgenerator.desktop.subprocess.run',side_effect=[SimpleNamespace(returncode=1,stdout='',stderr='test error'),SimpleNamespace(returncode=0,stdout='published',stderr='')]) as run:
            response=desktop._start_publications(jobs)
            self.assertEqual(response.status_code,200)
            thread.call_args.kwargs['target']()
            self.assertEqual(run.call_count,2)
            self.assertEqual(desktop._task['state'],'error')
            self.assertIn('one.exe — ОШИБКА',desktop._task['message'])
            self.assertIn('two.deb — опубликовано',desktop._task['message'])
