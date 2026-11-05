import io
import json
from pathlib import Path
import struct
import tempfile
from unittest.mock import patch
import uuid
import zipfile

from django.test import SimpleTestCase, override_settings, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from .local_build import local_status, get_local_record
from .build_downloads import library


class DownloadsTests(SimpleTestCase):
    def archive(self, bad=False):
        buffer = io.BytesIO()
        binary = bytearray(256)
        binary[:2] = b'MZ'
        struct.pack_into('<I', binary, 0x3c, 128)
        binary[128:134] = b'PE\0\0\x64\x86'
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr('../outside.exe' if bad else 'StatusDesk.exe', binary)
        return buffer.getvalue()

    def test_completed_build_downloads_once_and_refreshes_saved_status(self):
        payload = self.archive()
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def raise_for_status(self): pass
            def iter_content(self, size): yield payload
        identifier = str(uuid.uuid4())
        with tempfile.TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)):
            records = Path(directory) / '.local-builds'
            records.mkdir()
            (records / (identifier + '.json')).write_text(json.dumps({'id': identifier, 'workflow': 'generator-windows.yml',
                'run_id': 123, 'secret': 'test', 'branch': 'test', 'status': 'queued', 'cleaned': True}))
            def request(session, method, path, **kwargs):
                if path.endswith('/artifacts'):
                    return {'artifacts': [{'name': 'client-windows-x64', 'expired': False, 'archive_download_url': 'https://example.test/artifact'}]}
                return {'status': 'completed', 'conclusion': 'success', 'html_url': 'https://github.com/test/run'}
            with patch('rdgenerator.local_build.github_session') as session, patch('rdgenerator.local_build._request', side_effect=request):
                session.return_value.get.return_value = Response()
                self.assertEqual(local_status(identifier, download=True)['download_status'], 'completed')
                local_status(identifier, download=True)
                self.assertEqual(session.return_value.get.call_count, 1)
            self.assertEqual(get_local_record(identifier)['status'], 'completed')
            entries = library()
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]['platform'], 'windows-x64')
            self.assertTrue((Path(directory) / 'downloads' / entries[0]['relative_path']).is_file())

    def test_desktop_publication_is_local_and_csrf_protected(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.get('/desktop/installers', REMOTE_ADDR='10.0.0.1').status_code, 403)
        self.assertEqual(client.post('/desktop/publish', data='{}', content_type='application/json').status_code, 403)

    def test_import_detects_exe_architecture_and_returns_selectable_file(self):
        with zipfile.ZipFile(io.BytesIO(self.archive())) as archive:
            binary = archive.read('StatusDesk.exe')
        with tempfile.TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory), LOCAL_GITHUB_BUILD=True):
            response = Client().post('/desktop/import', {'file': SimpleUploadedFile('StatusDesk.exe', binary), 'platform': 'windows-x86', 'version': '1.5.0'}, REMOTE_ADDR='127.0.0.1')
            self.assertEqual(response.status_code, 200)
            item = library()[0]
            self.assertEqual(item['platform'], 'windows-x64')
            self.assertEqual(response.json()['id'], item['id'])
