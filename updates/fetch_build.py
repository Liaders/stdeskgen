"""Download a successful Windows generator artifact for an explicit release request."""
import argparse
import io
import json
import os
from pathlib import Path
import zipfile

import requests


def fetch(run_id, output, session=None, repository=None):
    repository = repository or os.environ['GITHUB_REPOSITORY']
    if session is None:
        session = requests.Session()
        session.headers.update({'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN'],
                                'Accept': 'application/vnd.github+json'})
    base = f'https://api.github.com/repos/{repository}'

    def get(path):
        result = session.get(base + path, timeout=60)
        result.raise_for_status()
        return result.json()

    run = get(f'/actions/runs/{int(run_id)}')
    if (run['conclusion'] != 'success' or run['event'] != 'workflow_dispatch'
            or run['path'] != '.github/workflows/generator-windows.yml'
            or run['head_branch'] != 'master'):
        raise ValueError('Only successful Windows generator builds from master can be published')
    artifacts = get(f'/actions/runs/{int(run_id)}/artifacts')['artifacts']
    candidates = [a for a in artifacts if a['name'] == 'client-windows-x64' and not a['expired']]
    if len(candidates) != 1:
        raise ValueError('Expected one non-expired Windows x64 artifact')
    response = session.get(base + f"/actions/artifacts/{candidates[0]['id']}/zip", timeout=600)
    response.raise_for_status()
    output.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        for item in archive.infolist():
            if '/' in item.filename or '\\' in item.filename or item.file_size > 512 * 1024 * 1024:
                raise ValueError('Unexpected artifact path or size')
            if item.filename == 'stdesk-update-build.json' or item.filename.endswith('.exe'):
                (output / item.filename).write_bytes(archive.read(item))
    if not (output / 'stdesk-update-build.json').exists():
        raise ValueError('This client was built without the signed update channel; rebuild it first')
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as stream:
            stream.write(f"commit={run['head_sha']}\n")
    return run['head_sha']


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    fetch(args.run_id, args.output)
