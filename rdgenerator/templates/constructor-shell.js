(() => {
    const el=id=>document.getElementById(id),form=el('myForm');
    function panel(name){
        document.querySelectorAll('[data-settings-panel]').forEach(p=>p.hidden=p.dataset.settingsPanel!==name);
        document.querySelectorAll('[data-panel]').forEach(b=>b.setAttribute('aria-current',b.dataset.panel===name?'page':'false'));
        try{sessionStorage.setItem('constructor-panel',name);}catch(_){}
    }
    document.querySelectorAll('[data-panel]').forEach(b=>b.onclick=()=>panel(b.dataset.panel));
    let initial='build';try{initial=sessionStorage.getItem('constructor-panel')||initial;}catch(_){}
    panel(document.querySelector('[data-settings-panel="'+initial.replace(/[^a-z]/g,'')+'"]')?initial:'build');
    function summary(){
        el('summary-version').textContent=el('id_version').value+'.'+(el('id_build_number').value||'…');
        el('summary-name').textContent=el('id_appname').value||'RustDesk';
        const platform=el('id_platform').selectedOptions[0]?.textContent||'Выберите платформу';
        el('summary-platform').textContent=platform;
        el('build-single').textContent='Собрать '+platform;
        document.querySelectorAll('.platform-icon').forEach(b=>{const active=b.dataset.platform===el('id_platform').value;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active));});
        el('summary-server').textContent=el('id_serverIP').value||'Не задан';
        const windows=['windows','windows-x86'].includes(el('id_platform').value);
        el('summary-updates').textContent=windows?(el('id_auto_update_enabled').disabled?'Недоступно для этой конфигурации':el('id_auto_update_enabled').checked?'Включено':'Выключено'):'Ручная установка';
        el('summary-appearance').textContent=el('id_platform').value==='windows-x86'?'Иконка и светлый логотип':el('ui-enabled').checked?'Настроено':'Стандартное';
        const target=el('summary-logo');
        const image=document.querySelector('#logodark-preview img, #logolight-preview img');
        const src=image?.getAttribute('src');
        if(target.dataset.source!==src){target.replaceChildren();if(src){const copy=document.createElement('img');copy.src=src;copy.alt='Логотип клиента';target.append(copy);}target.dataset.source=src||'';}
    }
    form.addEventListener('input',()=>{el('config-dirty').textContent='Есть изменения';summary();});
    form.addEventListener('change',summary);
    form.addEventListener('invalid',event=>{const page=event.target.closest('[data-settings-panel]');if(page)panel(page.dataset.settingsPanel);},true);
    new MutationObserver(summary).observe(el('client-version-preview'),{childList:true,characterData:true,subtree:true});
    for(const name of ['logolight-preview','logodark-preview'])new MutationObserver(summary).observe(el(name),{childList:true,subtree:true});
    el('create-next-release').addEventListener('click',()=>setTimeout(summary,100));
    el('ui-enabled').addEventListener('change',summary);
    window.rdgenConstructor={summary,panel};
    window.addEventListener('rdgen-config-loaded',()=>{el('config-dirty').textContent='Конфигурация загружена';summary();});
    summary();
})();
