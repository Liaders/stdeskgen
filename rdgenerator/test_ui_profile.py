from django.test import SimpleTestCase
from .forms import GenerateForm
from .api_views import validate_generate_params
from .views import generate_custom_client
from django.test import override_settings
import json


class UIProfileTests(SimpleTestCase):
    profile = {'schema_version': 1, 'accent': '#6750A4', 'navigation': 'text', 'group_width': 260, 'device_names': True, 'resizable_panels': True, 'slim_ui': True, 'organizations': True}

    def test_form_and_api_preserve_profile(self):
        raw = json.dumps(self.profile)
        form = GenerateForm(data={'version': '1.5.0', 'platform': 'windows', 'ui_profile': raw})
        form.is_valid()
        self.assertNotIn('ui_profile', form.errors)
        self.assertEqual(form.cleaned_data['ui_profile'], raw)
        cleaned, errors = validate_generate_params({'exename': 'Example', 'ui_profile': self.profile})
        self.assertFalse(errors)
        self.assertEqual(json.loads(cleaned['ui_profile']), self.profile)

    def test_unsupported_target_and_bad_profile_rejected(self):
        for extra in ({'version': 'master'}, {'platform': 'windows-x86'}, {'ui_profile': {'schema_version': 1, 'group_width': True}}, {'ui_profile': 'broken json'}, {'ui_profile': {'schema_version': 1, 'slim_ui': 'yes'}}, {'ui_profile': {'schema_version': 1, 'organizations': 'yes'}}):
            with self.subTest(extra=extra):
                _, errors = validate_generate_params({'exename': 'Example', 'ui_profile': self.profile, **extra})
                self.assertIn('ui_profile', errors)

    @override_settings(SH_SECRET='test-runner')
    def test_self_hosted_rejected_before_build_dispatch(self):
        result = generate_custom_client({'sh_secret_field': 'test-runner', 'ui_profile': self.profile}, 'https://example.test')
        self.assertFalse(result['success'])
        self.assertEqual(result['status_code'], 400)

    def test_old_api_configuration_has_no_profile(self):
        cleaned, errors = validate_generate_params({'exename': 'Example'})
        self.assertFalse(errors)
        self.assertEqual(cleaned['ui_profile'], '')

