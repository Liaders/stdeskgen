import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from download_catalog import update

class DownloadZipTests(unittest.TestCase):
    def test_both_architectures_keep_original_exe_and_channel(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            channel=root/'channels/statusdesk/stable/windows-x64.json'
            channel.parent.mkdir(parents=True);channel.write_bytes(b'unchanged update metadata')
            for platform,name in [('windows-x64','StatusDesk.exe'),('windows-x86','StatusDesk-x32.exe')]:
                folder=root/'releases/statusdesk/stable'/platform/'123';folder.mkdir(parents=True)
                exe=folder/('client-'+platform+'.exe');data=b'original installer '+platform.encode();exe.write_bytes(data)
                url='/client/'+exe.relative_to(root).as_posix()
                update(root,platform,url=url,version='1.5.1.4')
                item=json.loads((root/'downloads.json').read_text())['items'][platform]
                self.assertEqual(item['url'],url)
                archive=root/item['zip_url'].removeprefix('/client/')
                with zipfile.ZipFile(archive) as zipped:
                    self.assertEqual(zipped.namelist(),[name]);self.assertEqual(zipped.read(name),data)
                self.assertEqual(exe.read_bytes(),data)
            self.assertEqual(channel.read_bytes(),b'unchanged update metadata')
            self.assertEqual(len(json.loads((root/'downloads.json').read_text())['items']),2)

    def test_non_windows_unchanged_and_path_escape_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            update(root,'android-arm64',url='/client/downloads/client.apk',version='1.5.1.4')
            self.assertNotIn('zip_url',json.loads((root/'downloads.json').read_text())['items']['android-arm64'])
            with self.assertRaises(ValueError):
                update(root,'windows-x64',url='/client/../../other.exe',version='1.5.1.4')
