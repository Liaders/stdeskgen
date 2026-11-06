"""Restore local build assets and optional Flutter UI settings after checkout."""
import argparse
import base64
import json
import os
from pathlib import Path
import shutil
from apply_profile import apply
from desktop_chrome import apply_flutter
from theme_logos import stage

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--version', required=True)
parser.add_argument('--legacy', action='store_true')
args=parser.parse_args()
if not args.legacy: apply_flutter(Path.cwd())
assets=Path(os.environ['RUNNER_TEMP'])/'rdgen-input'
if assets.exists():
    if not args.legacy: stage(assets,Path('flutter/assets'))
    target=Path('.rdgen-input')
    target.mkdir(exist_ok=True)
    for name in ('icon.png','logo.png','logo_light.png','logo_dark.png','privacy.png'):
        if (assets/name).exists(): shutil.copyfile(assets/name,target/name)
profile=os.environ.get('ui_profile_b64')
if profile:
    apply(Path.cwd(),args.version,json.loads(base64.b64decode(profile,validate=True)))
