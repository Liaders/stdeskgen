"""Identify the code/templates loaded by a local constructor process."""
import hashlib
from pathlib import Path


def revision():
    root=Path(__file__).resolve().parent
    files=list(root.rglob('*.py'))+list((root/'templates').rglob('*.html'))+list((root/'templates').rglob('*.js'))
    digest=hashlib.sha256()
    for path in sorted(files):
        digest.update(path.relative_to(root).as_posix().encode('utf-8')+b'\0')
        digest.update(path.read_bytes()+b'\0')
    return digest.hexdigest()
