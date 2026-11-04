"""Restore local build assets and optional Flutter UI settings after checkout."""
import argparse
import base64
import json
import os
from pathlib import Path
import shutil
from apply_profile import apply

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--version', required=True)
args=parser.parse_args()
assets=Path(os.environ['RUNNER_TEMP'])/'rdgen-input'
if assets.exists():
    target=Path('.rdgen-input')
    target.mkdir(exist_ok=True)
    for name in ('icon.png','logo.png','privacy.png'):
        if (assets/name).exists(): shutil.copyfile(assets/name,target/name)
profile=os.environ.get('ui_profile_b64')
if profile:
    apply(Path.cwd(),args.version,json.loads(base64.b64decode(profile,validate=True)))
