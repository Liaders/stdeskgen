import json
from pathlib import Path
import tempfile

from django.test import SimpleTestCase, override_settings, Client
from unittest.mock import patch
from .version_numbers import reserve, next_number
from .default_config import load, save
from customization.versioning import revision


class VersionDefaultsTests(SimpleTestCase):
    def test_numbering_is_independent_per_base_and_does_not_reuse_numbers(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)):
            self.assertEqual(reserve('1.5.0'), '1.5.0.1')
            self.assertEqual(reserve('1.5.0'), '1.5.0.2')
            self.assertEqual(reserve('1.5.1'), '1.5.1.1')
            self.assertEqual(next_number('1.5.0'), 3)
            with self.assertRaises(ValueError): reserve('1.5.0', '1.5.0.1')
            self.assertLess(revision('1.5.0','1.5.0.999'), revision('1.5.1','1.5.1.1'))

    def test_missing_default_is_created_and_existing_settings_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)):
            first = load()
            self.assertEqual(first['appname'], 'StatusDesk')
            save({**first, 'serverIP': 'private.example', 'csrfmiddlewaretoken': 'discard'})
            self.assertEqual(load()['serverIP'], 'private.example')
            self.assertNotIn('csrfmiddlewaretoken', json.loads((Path(directory)/'default-config.json').read_text()))

    def test_default_is_embedded_on_get_and_saved_through_local_endpoint(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory), LOCAL_GITHUB_BUILD=True, ALLOWED_HOSTS=['testserver']), patch('rdgenerator.build_monitor.start'):
            client = Client()
            page = client.get('/', REMOTE_ADDR='127.0.0.1')
            self.assertEqual(page.status_code, 200)
            self.assertContains(page, 'default-config-data')
            response = client.post('/desktop/default-config', data=json.dumps({'appname':'MyDesk','version':'1.5.1'}), content_type='application/json', REMOTE_ADDR='127.0.0.1')
            self.assertEqual(response.status_code, 200)
            page = client.get('/', REMOTE_ADDR='127.0.0.1')
            self.assertContains(page, '"appname": "MyDesk"')
            self.assertEqual(client.get('/desktop/next-version?base=1.5.1', REMOTE_ADDR='127.0.0.1').json()['version'], '1.5.1.1')
            self.assertEqual(client.post('/desktop/default-config', data='{}', content_type='application/json', REMOTE_ADDR='10.0.0.1').status_code,403)
            self.assertEqual(Client(enforce_csrf_checks=True).post('/desktop/default-config', data='{}', content_type='application/json', REMOTE_ADDR='127.0.0.1').status_code,403)
