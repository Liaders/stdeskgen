"""Exercise libdrmtap staging after the workflow's actual branding commands."""
import ast
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest


class LinuxPackagingTests(unittest.TestCase):
    def test_branded_drm_packaging_creates_private_library_directory(self):
        generator=Path(__file__).resolve().parents[1]
        source=generator.parent/'rustdesk'
        original=subprocess.check_output(['git','-c',f'safe.directory={source.as_posix()}',
            '-C',str(source),'show',os.environ.get('RUSTDESK_TEST_REF','HEAD')+':build.py'])
        workflow=(generator/'.github/workflows/generator-linux.yml').read_text(encoding='utf-8')
        job=workflow.split('  build-rustdesk-linux-drm:',1)[1].split('\n  build-appimage:',1)[0]
        sed=shutil.which('sed')
        if not sed:
            sed=str(Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/native/git/usr/bin/sed.exe')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);build=root/'build.py';build.write_bytes(original)
            commands=re.findall(r'^\s*sed\s+(?:-ie|-i -e)\s+([\'"])(.*?)\1\s+(?:\./)?build\.py\s*$',job,re.M)
            self.assertGreater(len(commands),3)
            for quote,expression in commands:
                expression=expression.replace('${{ env.appname }}','StatusDesk').replace('${{ env.urlLink }}','https://example.test')
                if quote=='"':expression=re.sub(r'\\(["\\$`])',r'\1',expression)
                subprocess.run([sed,'-ie',expression,str(build)],check=True,capture_output=True)
            tree=ast.parse(build.read_text(encoding='utf-8'))
            function=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='stage_libdrmtap_into_deb')
            calls=[]
            def system2(command):
                parts=shlex.split(command);calls.append(parts)
                if parts[:2]==['mkdir','-p']:(root/parts[2]).mkdir(parents=True,exist_ok=True)
                elif parts[0]=='cp':shutil.copyfile(parts[1],root/parts[2]/Path(parts[1]).name)
                elif parts[:2]==['ln','-sf']:self.assertTrue((root/parts[3]).parent.is_dir())
                else:self.fail('Unexpected staging command: '+command)
            namespace={'os':os,'system2':system2,'assert_so_satisfies_the_runtime_abi_gate':lambda _:None}
            exec(compile(ast.Module(body=[function],type_ignores=[]),'<upstream staging>','exec'),namespace)
            native=root/'native bundle/libdrmtap.so.0.5.8';native.parent.mkdir();native.write_bytes(b'test native bytes')
            namespace[function.name](native.as_posix())
            self.assertEqual((root/'tmpdeb/usr/lib/rustdesk'/native.name).read_bytes(),native.read_bytes())
            self.assertEqual(calls[-1],['ln','-sf',native.name,'tmpdeb/usr/lib/rustdesk/libdrmtap.so.0'])
