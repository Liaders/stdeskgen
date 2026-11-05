(() => {
    const el=id=>document.getElementById(id), toggle=el('id_auto_update_enabled'), raw=el('id_updates_config');
    let channel=raw.value || '';
    function sync(){
        el('android-architecture').hidden=el('id_platform').value!=='android';
        if(raw.value)channel=raw.value;
        let reason='';
        if(!['windows','windows-x86'].includes(el('id_platform').value))reason='Для Linux/macOS/Android доступна ручная загрузка; автообновление пока поддерживает только Windows.';
        else if(!['1.5.0','1.5.1'].includes(el('id_version').value))reason='Эта базовая версия RustDesk пока не поддерживается нашим каналом.';
        else if(el('id_installation').value!=='installationY')reason='Автообновление требует клиента с разрешённой установкой.';
        else if(document.querySelector('[name=direction]:checked')?.value==='outgoing')reason='Автообновление требует клиента с поддержкой входящих подключений и службы Windows.';
        toggle.disabled=!!reason;
        raw.value=!reason && toggle.checked ? channel || JSON.stringify({base_url:'https://desk.status16.ru/client',product:'statusdesk',channel:'stable',revision:1}) : '';
        if(raw.value && !el('id_downloadLink').value)el('id_downloadLink').value='https://desk.status16.ru/client/';
        el('update-config-message').textContent=reason || (toggle.checked ? 'Клиент будет получать обновления с desk.status16.ru/client/. Версия определяется выбранным выпуском.' : 'Наш канал автоматического обновления отключён для этой сборки.');
    }
    for(const id of ['id_platform','id_version','id_installation','id_auto_update_enabled'])el(id).addEventListener('change',sync);
    for(const input of document.querySelectorAll('[name=direction]'))input.addEventListener('change',sync);
    el('myForm').addEventListener('submit',sync);
    window.rdgenUpdates={loadConfig(config){
        toggle.checked='auto_update_enabled' in config ? [true,'true','on',1].includes(config.auto_update_enabled) : true;
        channel=typeof config.updates_config==='object' && config.updates_config ? JSON.stringify(config.updates_config) : config.updates_config || '';
        raw.value='';
        sync();
    }};
    sync();
})();
