import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('pe',Path(__file__).with_name('verify_pe_arch.py'))
pe=importlib.util.module_from_spec(spec)
spec.loader.exec_module(pe)

class PEArchitectureTests(unittest.TestCase):
    def test_accepts_x86_and_rejects_x64_and_invalid_download(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'client.exe'
            data=bytearray(256)
            data[:2]=b'MZ'
            struct.pack_into('<I',data,0x3c,128)
            data[128:132]=b'PE\0\0'
            struct.pack_into('<H',data,132,0x14c)
            struct.pack_into('<H',data,152,0x10b)
            path.write_bytes(data)
            pe.verify_x86(path)
            struct.pack_into('<H',data,132,0x8664)
            struct.pack_into('<H',data,152,0x20b)
            path.write_bytes(data)
            with self.assertRaisesRegex(ValueError,'expected PE32'):
                pe.verify_x86(path)
            path.write_bytes(b'<html>404</html>')
            with self.assertRaisesRegex(ValueError,'not a Windows executable'):
                pe.verify_x86(path)
