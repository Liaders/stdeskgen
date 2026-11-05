import base64
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image
from verify_build_inputs import verify


class EmbeddedInputsTests(unittest.TestCase):
    def test_server_defaults_and_icon_must_match_requested_values(self):
        expected={'server':'id.example.test','serverPort':'21116','key':'test-public-key','apiServer':'https://api.example.test','iconlink_url':'local'}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            def write(name,data):
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(data,encoding='utf-8')
            source='pub const RENDEZVOUS_SERVERS: &[&str] = &["id.example.test"];\npub const RS_PUB_KEY: &str = "test-public-key";\n'
            for name,port in [('RENDEZVOUS_PORT',21116),('RELAY_PORT',21117),('WS_RENDEZVOUS_PORT',21118),('WS_RELAY_PORT',21119)]:
                source+=f'pub const {name}: i32 = {port};\n'
            write('libs/hbb_common/src/config.rs',source)
            write('src/common.rs','"https://api.example.test"')
            (root/'.rdgen-input').mkdir();(root/'res').mkdir()
            image=Image.new('RGBA',(64,64),'orange')
            image.save(root/'.rdgen-input/icon.png');image.save(root/'res/icon.png');image.save(root/'res/icon.ico')
            write('src/ui.rs',base64.b64encode((root/'res/icon.png').read_bytes()).decode())
            self.assertTrue(verify(root,expected,'windows-x86'))
            with self.assertRaisesRegex(ValueError,'ID server'):
                verify(root,{**expected,'server':'wrong.example.test'},'windows-x86')
            with self.assertRaisesRegex(ValueError,'public key'):
                verify(root,{**expected,'key':'wrong-key'},'windows-x86')
            with self.assertRaisesRegex(ValueError,'port'):
                verify(root,{**expected,'serverPort':'21117'},'windows-x86')
            with self.assertRaisesRegex(ValueError,'API server'):
                verify(root,{**expected,'apiServer':'https://wrong.example.test'},'windows-x86')
            write('src/ui.rs','original icon')
            with self.assertRaisesRegex(ValueError,'Sciter window icon'):
                verify(root,expected,'windows-x86')
