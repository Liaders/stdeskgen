"""Fetch the pinned Microsoft WebView2 SDK using the constructor's HTTPS stack."""
import base64
import hashlib
import io
from pathlib import Path
import zipfile

import requests

VERSION = '1.0.3650.58'
SHA512 = 'WDaTuak798It8pY8Y+2DG68qWZKwo5u1Ux8kDvaDiUexmsDhfqWdw1LR87YkEqdPa/14SEywVZRWzgtNoKKqqw=='


def prepare():
    root = Path(__file__).resolve().parents[1]
    target = root / '.tools' / ('webview2-' + VERSION)
    response = requests.get(f'https://api.nuget.org/v3-flatcontainer/microsoft.web.webview2/{VERSION}/microsoft.web.webview2.{VERSION}.nupkg', timeout=90)
    response.raise_for_status()
    if base64.b64encode(hashlib.sha512(response.content).digest()).decode() != SHA512:
        raise ValueError('Microsoft WebView2 SDK SHA-512 mismatch')
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        for name in ('lib/net462/Microsoft.Web.WebView2.Core.dll', 'lib/net462/Microsoft.Web.WebView2.WinForms.dll', 'runtimes/win-x64/native/WebView2Loader.dll'):
            path = target / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(archive.read(name))


if __name__ == '__main__':
    prepare()
