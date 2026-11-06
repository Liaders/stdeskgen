"""Stage custom theme logos before Flutter generates its asset manifest."""
import argparse
from pathlib import Path
import shutil

LOGOS = ('logo.png', 'logo_light.png', 'logo_dark.png')

def stage(assets, destination):
    supplied = {name: (assets/name).read_bytes() for name in LOGOS if (assets/name).is_file()}
    if not supplied:
        return
    fallback = next(supplied[name] for name in LOGOS if name in supplied)
    destination.mkdir(parents=True, exist_ok=True)
    for name in LOGOS:
        data = supplied.get(name, fallback)
        (assets/name).write_bytes(data)
        (destination/name).write_bytes(data)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    stage(args.assets, args.destination)
