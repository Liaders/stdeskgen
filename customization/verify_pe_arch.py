"""Fail the Windows x86 build if its executable or runtime is not PE32/i386."""
import argparse
from pathlib import Path
import struct


def verify_x86(path):
    data=Path(path).read_bytes()
    if len(data)<64 or data[:2]!=b'MZ': raise ValueError(f'{path}: not a Windows executable')
    offset=struct.unpack_from('<I',data,0x3c)[0]
    if offset+26>len(data) or data[offset:offset+4]!=b'PE\0\0': raise ValueError(f'{path}: invalid PE header')
    machine=struct.unpack_from('<H',data,offset+4)[0]
    kind=struct.unpack_from('<H',data,offset+24)[0]
    if (machine,kind)!=(0x14c,0x10b): raise ValueError(f'{path}: expected PE32/i386, got machine={machine:#x}, kind={kind:#x}')
    print(f'Confirmed Windows x86: {Path(path).name}')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files',nargs='+')
    for name in parser.parse_args().files: verify_x86(name)
