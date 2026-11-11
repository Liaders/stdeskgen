"""Thin local IPC and UI hooks for the configured StatusDesk update channel."""
import json
from pathlib import Path

COMMANDS = '"rdgen-update-check" | "rdgen-update-install" | "rdgen-update-status"'


def stage(root, edits, platform):
    def replace(name, old, new):
        path = root/name
        source = edits.get(path, path.read_text(encoding='utf-8'))
        if source.count(old) != 1:
            raise ValueError('Incompatible manual updater source: '+name)
        edits[path] = source.replace(old, new, 1)

    replace('src/ipc.rs', '''        Data::Config((name, value)) => match value {
            None => {''', '''        Data::Config((name, value)) => match value {
            None => {
                #[cfg(target_os = "windows")]
                if matches!(name.as_str(), '''+COMMANDS+''') {
                    let value = crate::updater::rdgen_update::manual_command(&name);
                    allow_err!(stream.send(&Data::Config((name, Some(value)))).await);
                    return;
                }''')
    replace('src/ui_interface.rs', 'pub fn get_option<T: AsRef<str>>(key: T) -> String {',
            '''pub fn get_option<T: AsRef<str>>(key: T) -> String {
    #[cfg(target_os = "windows")]
    if matches!(key.as_ref(), '''+COMMANDS+''') {
        return match crate::ipc::get_config(key.as_ref()) {
            Ok(Some(value)) => value,
            _ => serde_json::json!({"status":"error","message":"Update service is unavailable"}).to_string(),
        };
    }''')
    if platform == 'windows-x86':
        path = root/'src/ui/index.tis'
        source = path.read_text(encoding='utf-8')
        anchor = '                    {software_update_url && !disable_installation ? <UpdateMe /> : ""}'
        if source.count(anchor) != 1: raise ValueError('Incompatible Sciter update card')
        edits[path] = Path(__file__).with_name('client_card.tis').read_text(encoding='utf-8')+'\n'+source.replace(anchor,
            '                    {is_win && handler.is_installed() && !disable_installation ? <RdgenUpdateCard /> : ""}\n'+anchor, 1)
    else:
        replace('src/flutter_ffi.rs', 'pub fn main_get_common(key: String) -> String {',
                '''pub fn main_get_common(key: String) -> String {
    #[cfg(target_os = "windows")]
    if matches!(key.as_str(), '''+COMMANDS+''') {
        return crate::ui_interface::get_option(key);
    }''')
        home = 'flutter/lib/desktop/pages/desktop_home_page.dart'
        path = root/home
        edits[path] = "import '../../models/rdgen_update_card.dart';\n"+path.read_text(encoding='utf-8')
        replace(home, '      if (!isOutgoingOnly) buildPasswordBoard(context),',
                '      if (!isOutgoingOnly) buildPasswordBoard(context),\n      const RdgenUpdateCard(),')
        edits[root/'flutter/lib/models/rdgen_update_card.dart'] = Path(__file__).with_name('client_card.dart').read_text(encoding='utf-8')
    labels = {
        'Check for updates': 'Проверить обновления',
        'Checking for updates': 'Проверка обновлений',
        'Downloading update': 'Скачивание обновления',
        'Starting update installation': 'Запускается установка обновления',
        'Latest version installed': 'Установлена последняя версия',
        'New version available': 'Доступна новая версия',
        'Update check failed': 'Не удалось проверить обновления',
        'Update service is unavailable': 'Служба обновления недоступна. Перезапустите службу StatusDesk.',
        'Close active sessions before updating': 'Завершите активные подключения перед обновлением',
        'Installed StatusDesk service is required': 'Для обновления нужна установленная служба StatusDesk',
        'Installation is disabled by policy': 'Установка запрещена настройками',
        'StatusDesk EXE updates do not support MSI installations yet': 'Автообновление MSI пока не поддерживается',
        'Auto update was disabled before installation': 'Автообновление отключено перед установкой',
    }
    for path in (root/'src/lang').glob('*.rs'):
        if path.name == 'en.rs': continue
        text = edits.get(path, path.read_text(encoding='utf-8'))
        missing = {k:v for k,v in labels.items() if json.dumps(k) not in text}
        if not missing: continue
        anchor = '    ].iter().cloned().collect();'
        if text.count(anchor) != 1: raise ValueError('Incompatible updater translation')
        prefix, suffix = text.split(anchor)
        entries = ''.join('\n        ('+json.dumps(k)+', '+json.dumps(v if path.name == 'ru.rs' else '',ensure_ascii=False)+'),' for k,v in missing.items())
        edits[path] = prefix.rstrip().removesuffix(',')+','+entries+'\n'+anchor+suffix
