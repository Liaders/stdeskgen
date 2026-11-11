#!/usr/bin/env bash
set -euo pipefail
: "${RDGEN_APP_NAME:?}"
: "${RDGEN_FILENAME:?}"
: "${RDGEN_APPIMAGE_ARCH:?}"
tools_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
sudo python3 "$tools_dir/ubuntu_apt.py"
export RDGEN_PACKAGE_VERSION="$(dpkg-deb -f appimage/rustdesk.deb Version)"
python3 - <<'PY'
import json, os, re
from pathlib import Path
recipe=Path('appimage')/('AppImageBuilder-'+os.environ['RDGEN_APPIMAGE_ARCH']+'.yml')
text,count=re.subn(r'^    version:.*$',lambda _: '    version: '+json.dumps(os.environ['RDGEN_PACKAGE_VERSION']),recipe.read_text(),count=1,flags=re.M)
if count!=1:raise SystemExit('Missing AppImage package version')
recipe.write_text(text)
PY
if [ "${RDGEN_APP_NAME}" != "rustdesk" ] && [ "${RDGEN_APP_NAME}" != "RustDesk" ]; then
  # The recipe's script does `bsdtar -zxvf rustdesk.deb`, so after the sed
  # below it looks for <appname>.deb -- the deb must end up under exactly
  # that name. Renaming it to <filename>.deb only matched when appname and
  # filename happened to be equal. The deb is moved out of the way first
  # because `appimage/*` globs it too, and sed over an ar archive rewrites
  # bytes inside it.
  mv appimage/rustdesk.deb "${RUNNER_TEMP}/appimage-payload.deb"
  sed -ie "s|rustdesk|${RDGEN_APP_NAME}|g" appimage/*
  mv "${RUNNER_TEMP}/appimage-payload.deb" "appimage/${RDGEN_APP_NAME}.deb"
fi
sudo apt-get update -y
sudo apt-get install -y libarchive-tools libfuse2 ubuntu-keyring gnupg
sudo pip3 install "setuptools_scm<10"
sudo pip3 install git+https://github.com/rustdesk-org/appimage-builder.git
if [ "${RDGEN_APPIMAGE_ARCH}" = "aarch64" ]; then
  python3 "$tools_dir/appimage_keys.py" \
    --recipe appimage/AppImageBuilder-aarch64.yml \
    --output "${RUNNER_TEMP}/rdgen-ubuntu-archive.asc"
fi
pushd appimage
sudo appimage-builder --skip-tests --recipe ./AppImageBuilder-${RDGEN_APPIMAGE_ARCH}.yml
# recipe output is <name>-<version>-<arch>.AppImage, where <version> is the
# version stamped in AppImageBuilder-<arch>.yml -- NOT the workflow's VERSION
# input. They coincide for a tagged build, which is why globbing on VERSION
# worked there, but a master build passes VERSION=master while the recipe
# still carries a release number, so the glob matched nothing:
#   mv: cannot stat './*-master-x86_64.AppImage': No such file or directory
# Match on the arch suffix instead, and exclude the destination name so this
# can never try to move a file onto itself.
dest="${RDGEN_FILENAME}-${RDGEN_APPIMAGE_ARCH}.AppImage"
src=$(find . -maxdepth 1 -name "*-${RDGEN_APPIMAGE_ARCH}.AppImage" ! -name "$dest" | head -1)
if [ -z "$src" ]; then
  echo "::error::no *-${RDGEN_APPIMAGE_ARCH}.AppImage produced by appimage-builder"; ls -l; exit 1
fi
sudo mv "$src" "./$dest"
popd
