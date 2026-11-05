"""Disable upstream update checks without editing neighboring response handlers."""
import argparse
from pathlib import Path


def apply(root):
    path = root / 'src/common.rs'
    source = path.read_text(encoding='utf-8')
    anchor = 'pub async fn do_check_software_update() -> hbb_common::ResultType<()> {'
    if source.count(anchor) != 1:
        raise ValueError('Incompatible upstream update check')
    start = source.index(anchor) + len(anchor)
    end = source.index('\n}', start)
    path.write_text(source[:start] + '\n    Ok(())' + source[end:], encoding='utf-8')
    page = root / 'flutter/lib/desktop/pages/desktop_home_page.dart'
    if page.exists():
        page.write_text(page.read_text(encoding='utf-8').replace('updateUrl.isNotEmpty', 'false'), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=Path('.'))
    apply(parser.parse_args().source)
