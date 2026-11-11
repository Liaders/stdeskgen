"""Connect the original RustDesk update cards to the StatusDesk service channel."""
import json
from pathlib import Path

COMMANDS = '"rdgen-update-install" | "rdgen-update-status"'


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
        start = source.index('class UpdateMe: Reactor.Component {')
        end = source.index('class SystemError:', start)
        card = source[start:end]
        title = '<div>There is a newer version of {handler.get_app_name()} ({handler.get_new_version()}) available.</div>'
        if card.count(title) != 1: raise ValueError('Incompatible original Sciter update card')
        card = card.replace(title, "<div>{translate('New version available')} {rdgen_update_state.version}</div>")
        custom = card.index('            {is_custom_client')
        progress = card.index('            <div #download-percent',custom)
        card = card[:custom]+"            <div #install-me.link>{translate('Update')}</div>\n"+card[progress:]
        click = card.index('    event click $(#install-me) {')
        card = card[:click]+"    event click $(#install-me) { rdgenInstallUpdate(); }\n}\n\n"
        source = source[:start]+card+source[end:]
        if source.count('tmp = handler.get_software_update_url();') != 1:
            raise ValueError('Incompatible original Sciter update polling')
        source = source.replace('tmp = handler.get_software_update_url();','tmp = rdgenUpdateCardUrl();',1)
        edits[path] = Path(__file__).with_name('stock_card.tis').read_text(encoding='utf-8')+'\n'+source
    else:
        replace('src/flutter_ffi.rs', 'pub fn main_get_common(key: String) -> String {',
                '''pub fn main_get_common(key: String) -> String {
    #[cfg(target_os = "windows")]
    if matches!(key.as_str(), '''+COMMANDS+''') {
        return crate::ui_interface::get_option(key);
    }''')
        home = 'flutter/lib/desktop/pages/desktop_home_page.dart'
        path = root/home
        edits[path] = "import '../../models/rdgen_stock_update.dart';\n"+path.read_text(encoding='utf-8')
        replace(home, '  Widget buildHelpCards(String updateUrl) {', '''  Widget buildHelpCards(String updateUrl) {
    if (isWindows && bind.mainIsInstalled() && !bind.isDisableInstallation() &&
        updateUrl.startsWith(rdgenUpdatePrefix) && !isCardClosed) {
      final version = Uri.decodeComponent(updateUrl.substring(rdgenUpdatePrefix.length));
      return buildInstallCard("Status",
        "${translate("new-version-of-{${bind.mainGetAppNameSync()}}-tip")} ($version).",
        'Update', () { rdgenInstallUpdate(); }, closeButton: true);
    }''')
        replace(home, '      await gFFI.serverModel.fetchID();',
                '      await rdgenPollUpdateCard();\n      await gFFI.serverModel.fetchID();')
        edits[root/'flutter/lib/models/rdgen_stock_update.dart'] = Path(__file__).with_name('stock_card.dart').read_text(encoding='utf-8')
    labels = {
        'Checking for updates': 'Проверка обновлений',
        'Downloading update': 'Скачивание обновления',
        'Starting update installation': 'Запускается установка обновления',
        'New version available': 'Доступна новая версия',
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
