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
        form = GenerateForm(data={'exename': 'StatusDesk', 'version': '1.5.0', 'platform': 'windows', 'updates_config': raw})
        form.is_valid()
        self.assertNotIn('updates_config', form.errors)
        self.assertEqual(form.cleaned_data['updates_config'], raw)
        cleaned, errors = validate_generate_params({'exename': 'StatusDesk', 'updates_config': self.config})
        self.assertFalse(errors)
        self.assertEqual(json.loads(cleaned['updates_config']), self.config)

    def test_reject_unsupported_platform(self):
        _, errors = validate_generate_params({'exename': 'StatusDesk', 'platform': 'windows-x86', 'updates_config': self.config})
        self.assertIn('updates_config', errors)

    @override_settings(LOCAL_GITHUB_BUILD=True, SH_SECRET='unused-test-secret')
    @patch('rdgenerator.views.dispatch_local')
    def test_unsupported_configuration_never_dispatches(self, dispatch):
        for extra in ({'installation': 'installationN'}, {'direction': 'outgoing'}, {'update_public_key': 'legacy-key'}):
            with self.subTest(extra=extra):
                result = generate_custom_client({'exename': 'StatusDesk', 'updates_config': self.config, **extra}, 'http://127.0.0.1:8765')
                self.assertEqual(result['status_code'], 400)
        dispatch.assert_not_called()
