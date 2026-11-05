import base64
import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
import pyzipper
from django.test import SimpleTestCase, override_settings
from nacl.public import PrivateKey, SealedBox
from .local_build import pack_configuration, dispatch_local, LocalBuildError
from .views import generate_custom_client


class LocalBuildTests(SimpleTestCase):
    def test_configuration_and_assets_are_encrypted(self):
        payload, password = pack_configuration({'custom': 'test-password'}, {'icon.png': b'png-test'})
        self.assertNotIn(b'test-password', payload)
        with pyzipper.AESZipFile(io.BytesIO(payload)) as archive:
            archive.setpassword(password.encode())
            self.assertEqual(json.loads(archive.read('secrets.json')), {'custom': 'test-password'})
            self.assertEqual(archive.read('icon.png'), b'png-test')

    @override_settings(GHUSER='Liaders', REPONAME='stdeskgen', GHBRANCH='master')
    def test_dispatch_sends_only_ciphertext_and_identifiers(self):
        private = PrivateKey.generate()
        calls = []
        def request(session, method, path, **kwargs):
            calls.append((method, path, kwargs))
            if path.endswith('public-key'):
                return {'key_id': 'test', 'key': base64.b64encode(bytes(private.public_key)).decode()}
            if path.startswith('/git/ref/'):
                return {'object': {'sha': 'abc'}}
            return {}
        with tempfile.TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)):
            with patch('rdgenerator.local_build.github_session'), patch('rdgenerator.local_build._request', side_effect=request):
                result = dispatch_local({'filename': 'Client', 'custom': 'private-setting'}, {}, '1.5.0')
            self.assertTrue(result['local_build'])
            dispatch = calls[-1][2]['json']
            self.assertNotIn('private-setting', json.dumps(dispatch))
            secret = next(c[2]['json'] for c in calls if '/actions/secrets/STDESK' in c[1])
            password = SealedBox(private).decrypt(base64.b64decode(secret['encrypted_value']))
            content = next(c[2]['json']['content'] for c in calls if c[1]=='/contents/build-input.zip')
            with pyzipper.AESZipFile(io.BytesIO(base64.b64decode(content))) as archive:
                archive.setpassword(password)
                self.assertEqual(json.loads(archive.read('secrets.json'))['custom'], 'private-setting')

    @override_settings(LOCAL_GITHUB_BUILD=True, SH_SECRET='unused')
    def test_form_configuration_uses_local_transport(self):
        with patch('rdgenerator.views.dispatch_local', return_value={'success':True,'local_build':True}) as dispatch:
            result=generate_custom_client({'platform':'windows','version':'1.5.0','exename':'Test',
                'serverIP':'example.test','permanentPassword':'secret-test','ui_profile':'{"schema_version":1,"device_names":true}'}, 'http://127.0.0.1:8765')
        self.assertTrue(result['success'])
        inputs=dispatch.call_args.args[0]
        self.assertEqual(inputs['server'], 'example.test')
        self.assertEqual(inputs['iconlink_url'], 'false')
        self.assertTrue(json.loads(base64.b64decode(inputs['ui_profile_b64']))['device_names'])

    @override_settings(LOCAL_GITHUB_BUILD=True)
    def test_unsupported_platform_never_dispatches(self):
        with patch('rdgenerator.views.dispatch_local') as dispatch:
            result=generate_custom_client({'platform':'android','exename':'Test'}, 'http://127.0.0.1:8765')
        self.assertFalse(result['success'])
        dispatch.assert_not_called()

    @override_settings(LOCAL_GITHUB_BUILD=True, SH_SECRET='unused')
    def test_supported_platforms_route_to_their_workflows(self):
        for platform in ('windows-x86','linux','macos'):
            with self.subTest(platform=platform), patch('rdgenerator.views.dispatch_local',return_value={'success':True}) as dispatch:
                result=generate_custom_client({'platform':platform,'version':'1.5.0','exename':'Test'},'http://127.0.0.1:8765')
                self.assertTrue(result['success'])
                self.assertEqual(dispatch.call_args.kwargs['platform'],platform)

    @override_settings(LOCAL_GITHUB_BUILD=True, SH_SECRET='unused')
    def test_x86_ignores_visual_assets_and_theme(self):
        with patch('rdgenerator.views.dispatch_local',return_value={'success':True}) as dispatch:
            result=generate_custom_client({'platform':'windows-x86','version':'1.5.1','exename':'Test','theme':'dark',
                'iconbase64':'invalid-custom-icon','logobase64':'invalid-logo','privacybase64':'invalid-privacy'},'http://127.0.0.1:8765')
        self.assertTrue(result['success'])
        inputs, images = dispatch.call_args.args[:2]
        self.assertEqual(images,{})
        self.assertEqual(inputs['iconlink_url'],'false')
        self.assertNotIn('allow-darktheme', inputs['custom'])
