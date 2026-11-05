"""GitHub downloads a locally signed package; it never receives a signing key."""
import argparse
import hashlib
import os
from pathlib import Path
import re

import requests
from signed_bundle import unpack


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--release-id', type=int, required=True)
    parser.add_argument('--asset-id', type=int, required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch('[0-9a-f]{64}', args.sha256):
        raise ValueError('Invalid package SHA-256')
    session = requests.Session()
    session.headers.update({'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN'], 'Accept': 'application/vnd.github+json'})
    base = 'https://api.github.com/repos/' + os.environ['GITHUB_REPOSITORY']
    release = session.get(base + f'/releases/{args.release_id}', timeout=30)
    release.raise_for_status()
    if not any(item['id'] == args.asset_id and item['name'] == 'signed-client-update.zip' for item in release.json()['assets']):
        raise ValueError('Asset does not belong to the specified release')
    response = session.get(base + f'/releases/assets/{args.asset_id}', headers={'Accept': 'application/octet-stream'}, timeout=600)
    response.raise_for_status()
    if hashlib.sha256(response.content).hexdigest() != args.sha256:
        raise ValueError('Package SHA-256 mismatch')
    manifest = unpack(response.content, os.environ['STDESK_UPDATE_PUBLIC_KEY'], args.output)
    print(f"Verified locally signed {manifest['product']}/{manifest['channel']} revision {manifest['revision']}")
