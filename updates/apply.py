"""Install the isolated update path without rewriting the upstream updater."""
import argparse
import json
import os
import re
import base64
from pathlib import Path
from config import validate


def apply(root, config, platform='windows'):
    if config in (None, ''):
        return
    cargo = (root / 'Cargo.toml').read_text(encoding='utf-8')
    match = re.search(r'^version = "([^"]+)"', cargo, re.M)
    if not match:
        raise ValueError('Cannot determine upstream RustDesk version')
    version = match[1]
    config = validate(config, version=version, platform=platform)
    if config is None:
        return
    updater = root / 'src/updater.rs'
    source = updater.read_text(encoding='utf-8')
    anchor = 'fn check_update(manually: bool) -> ResultType<()> {'
    if source.count(anchor) != 1 or 'mod rdgen_update' in source:
        raise ValueError('Incompatible or already customized updater source')
    common = root / 'src/common.rs'
    common_source = common.read_text(encoding='utf-8')
    stock_check = 'pub async fn do_check_software_update() -> hbb_common::ResultType<()> {'
    if common_source.count(stock_check) != 1:
        raise ValueError('Incompatible upstream update check')
    module = Path(__file__).with_name('client.rs').read_text(encoding='utf-8')
    target_platform = 'windows-x86' if platform == 'windows-x86' else 'windows-x64'
    module = module.replace('@PLATFORM@', json.dumps(target_platform))
    install_call = ('super::update_new_version(false, &release.version, &path);' if version == '1.5.0'
                    else 'super::update_new_version(false, &release.version, &path, &release.sha256);')
    module = module.replace('@INSTALL_VERIFIED_UPDATE@', install_call)
    for name, field in [('BASE', 'base_url'), ('PRODUCT', 'product'), ('CHANNEL', 'channel'), ('REVISION', 'revision')]:
        module = module.replace('@' + name + '@', json.dumps(config[field]))
    hook = '#[cfg(target_os = "windows")]\n#[path = "rdgen_update.rs"]\npub(crate) mod rdgen_update;\n'
    source = hook + source.replace(anchor, anchor + '\n    #[cfg(target_os = "windows")]\n    return rdgen_update::check();\n', 1)
    start = source.index('fn start_auto_update_check_(rx_msg: Receiver<UpdateMsg>) {')
    end = source.index(anchor, start)
    schedule = source[start:end]
    if schedule.count('DUR_ONE_DAY') != 2:
        raise ValueError('Incompatible update check interval')
    schedule = schedule.replace('DUR_ONE_DAY', 'RETRY_INTERVAL')
    active_gate = """                // Don't check update if there are alive connections.
                if !has_no_active_conns() {
                    check_interval = RETRY_INTERVAL;
                    continue;
                }
"""
    if schedule.count(active_gate) != 1:
        raise ValueError('Incompatible update session gate')
    schedule = schedule.replace(active_gate, '', 1)
    source = source[:start]+schedule+source[end:]
    # Quote the installer path: the Windows user profile/temp path may contain spaces.
    source = source.replace('&format!("{} --update", p)', '&format!("\\\"{}\\\" --update", p)')
    edits = {root/'src/rdgen_update.rs': module, updater: source,
             common: common_source.replace(stock_check, stock_check + '\n    return Ok(()); // The StatusDesk updater owns this build.', 1)}
    from manual import stage
    stage(root, edits, platform)
    for path, text in edits.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
    receipt = {**config, 'schema': 2, 'platform': target_platform}
    (root / 'stdesk-update-build.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=Path('.'))
    parser.add_argument('--platform', default='windows', choices=('windows','windows-x86'))
    args = parser.parse_args()
    raw = base64.b64decode(os.environ['stdesk_update_b64'], validate=True)
    apply(args.source, json.loads(raw), args.platform)
    receipt_path = args.source / 'stdesk-update-build.json'
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    app = os.environ.get('appname', 'RustDesk')
    receipt['app_name'] = 'RustDesk' if app == 'rustdesk' else app
    match = re.search(r'^version = "([^"]+)"', (args.source / 'Cargo.toml').read_text(encoding='utf-8'), re.M)
    if not match:
        raise ValueError('Cannot read compiled application version')
    receipt['version'] = os.environ.get('stdesk_display_version') or match[1]
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
