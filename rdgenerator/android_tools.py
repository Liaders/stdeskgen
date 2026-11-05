"""Fetch official Java runtime and Android signing tools; keys never leave this PC."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile
import xml.etree.ElementTree as ET
import requests
from django.conf import settings


def _download(url,path,digest,algorithm):
    temporary=path.with_suffix('.part');hasher=hashlib.new(algorithm);total=0
    with requests.get(url,stream=True,timeout=300) as response:
        response.raise_for_status()
        with temporary.open('wb') as output:
            for data in response.iter_content(1048576):
                total+=len(data)
                if total>500*1024**2:raise ValueError('Android tooling archive exceeds 500 MB')
                output.write(data);hasher.update(data)
    if hasher.hexdigest().lower()!=digest.lower():raise ValueError('Android tooling archive checksum mismatch')
    temporary.replace(path)


def _extract(path,target):
    target.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            relative=PurePosixPath(info.filename)
            if relative.is_absolute() or '..' in relative.parts or ':' in info.filename or '\\' in info.filename:raise ValueError('Unsafe tooling archive path')
            if not (target/relative).resolve().is_relative_to(target.resolve()):raise ValueError('Unsafe tooling extraction')
        archive.extractall(target)


def ensure_tools():
    root=Path(settings.BASE_DIR)/'.tools/android';root.mkdir(parents=True,exist_ok=True)
    marker=root/'tools.json'
    if marker.exists():
        result=json.loads(marker.read_text(encoding='utf-8'))
        if all(Path(p).is_file() and Path(p).resolve().is_relative_to(root.resolve()) for p in result.values()):return result
    metadata=requests.get('https://api.adoptium.net/v3/assets/latest/17/hotspot',params={'architecture':'x64','image_type':'jre','os':'windows','vendor':'eclipse'},timeout=60)
    metadata.raise_for_status();package=metadata.json()[0]['binary']['package']
    if not package['link'].startswith('https://github.com/adoptium/temurin17-binaries/'):raise ValueError('Unexpected Java runtime source')
    archive=root/'java.zip';_download(package['link'],archive,package['checksum'],'sha256');_extract(archive,root/'java')
    response=requests.get('https://dl.google.com/android/repository/repository2-3.xml',timeout=60);response.raise_for_status()
    tree=ET.fromstring(response.content)
    package=next(p for p in tree.iter('remotePackage') if p.attrib.get('path')=='build-tools;36.0.0')
    archive_info=next(a for a in package.findall('./archives/archive') if a.findtext('host-os')=='windows')
    complete=archive_info.find('complete');url=complete.findtext('url');checksum=complete.find('checksum')
    if not url or '/' in url or '\\' in url:raise ValueError('Unexpected Android tools archive')
    archive=root/'build-tools.zip';_download('https://dl.google.com/android/repository/'+url,archive,checksum.text,checksum.attrib.get('type','sha1'));_extract(archive,root/'sdk')
    java=next((root/'java').rglob('java.exe'));keytool=java.with_name('keytool.exe');signer=next((root/'sdk').rglob('apksigner.jar'));sdk=signer.parent.parent
    result={'java':str(java.resolve()),'keytool':str(keytool.resolve()),'signer':str(signer.resolve()),'zipalign':str((sdk/'zipalign.exe').resolve()),'aapt':str((sdk/'aapt.exe').resolve())}
    if not all(Path(p).is_file() for p in result.values()):raise ValueError('Android signing tools are incomplete')
    marker.write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result
