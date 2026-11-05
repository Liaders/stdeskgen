import json
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from .api_views import validate_generate_params
from .forms import GenerateForm
from .views import generate_custom_client


class UpdateChannelTests(SimpleTestCase):
    config = {'base_url': 'https://desk.status16.ru/client',
              'product': 'statusdesk', 'channel': 'test', 'revision': 1}

    def test_form_and_api_preserve_optional_config(self):
        raw = json.dumps(self.config)
        form = GenerateForm(data={'exename': 'StatusDesk', 'version': '1.5.0', 'platform': 'windows', 'auto_update_enabled': True, 'updates_config': raw})
        form.is_valid()
        self.assertNotIn('updates_config', form.errors)
        self.assertEqual(form.cleaned_data['updates_config'], raw)
        cleaned, errors = validate_generate_params({'exename': 'StatusDesk', 'updates_config': self.config})
        self.assertFalse(errors)
        self.assertEqual(json.loads(cleaned['updates_config']), self.config)

    def test_reject_unsupported_platform(self):
        _, errors = validate_generate_params({'exename': 'StatusDesk', 'platform': 'linux', 'updates_config': self.config})
        self.assertIn('updates_config', errors)

    @override_settings(LOCAL_GITHUB_BUILD=True, SH_SECRET='unused-test-secret')
    @patch('rdgenerator.views.dispatch_local', return_value={'success': True})
    def test_channel_enables_updates_by_default_and_respects_explicit_setting(self, dispatch):
        import base64
        for version, manual, expected in (('1.5.0', '', 'Y'), ('1.5.1', '', 'Y'), ('1.5.1', 'allow-auto-update=N', 'N')):
            result = generate_custom_client({'exename': 'StatusDesk', 'version': version, 'updates_config': self.config, 'defaultManual': manual}, 'http://127.0.0.1:8765')
            self.assertTrue(result['success'])
            custom = json.loads(base64.b64decode(dispatch.call_args.args[0]['custom']))
            self.assertEqual(custom['default-settings']['allow-auto-update'], expected)

    @override_settings(LOCAL_GITHUB_BUILD=True, SH_SECRET='unused-test-secret')
    @patch('rdgenerator.views.dispatch_local')
    def test_unsupported_configuration_never_dispatches(self, dispatch):
        for extra in ({'installation': 'installationN'}, {'direction': 'outgoing'}, {'update_public_key': 'legacy-key'}):
            with self.subTest(extra=extra):
                result = generate_custom_client({'exename': 'StatusDesk', 'updates_config': self.config, **extra}, 'http://127.0.0.1:8765')
                self.assertEqual(result['status_code'], 400)
        dispatch.assert_not_called()

    @override_settings(LOCAL_GITHUB_BUILD=True, SH_SECRET='unused-test-secret')
    @patch('rdgenerator.views.dispatch_local', return_value={'success': True})
    def test_default_channel_and_explicit_opt_out(self, dispatch):
        import base64
        for platform in ('windows','windows-x86'):
            result=generate_custom_client({'exename':'Test','platform':platform,'version':'1.5.1'},'http://127.0.0.1:8765')
            self.assertTrue(result['success'])
            config=json.loads(base64.b64decode(dispatch.call_args.args[0]['stdesk_update_b64']))
            self.assertEqual(config['channel'],'stable')
            self.assertEqual(config['base_url'],'https://desk.status16.ru/client')
        result=generate_custom_client({'exename':'Test','auto_update_enabled':False,'updates_config':self.config,'defaultManual':'allow-auto-update=Y'},'http://127.0.0.1:8765')
        self.assertTrue(result['success'])
        inputs=dispatch.call_args.args[0]
        self.assertNotIn('stdesk_update_b64',inputs)
        custom=json.loads(base64.b64decode(inputs['custom']))
        self.assertEqual(custom['override-settings']['allow-auto-update'],'N')
        cleaned,errors=validate_generate_params({'exename':'Test','auto_update_enabled':False,'updates_config':self.config})
        self.assertFalse(errors)
        self.assertEqual(cleaned['updates_config'],'')
        for extra in ({'platform':'linux'},{'platform':'macos'},{'installation':'installationN'},{'direction':'outgoing'}):
            result=generate_custom_client({'exename':'Test',**extra},'http://127.0.0.1:8765')
            self.assertTrue(result['success'])
            self.assertNotIn('stdesk_update_b64',dispatch.call_args.args[0])
