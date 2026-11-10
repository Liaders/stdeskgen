(() => {
    const el=id=>document.getElementById(id), form=el('myForm');
    form.addEventListener('submit',async event=>{
        if(event.defaultPrevented)return;
        const all=event.submitter?.value==='all';
        if(all){
            try{el('batch-ui-profile').value=window.rdgenUI.batchProfile();}
            catch(error){event.preventDefault();alert(error.message);return;}
            el('batch-auto-update-enabled').value=el('id_auto_update_enabled').checked?'on':'';
        }
        const targets=all?'Windows x64, Windows x86, Linux, macOS и Android':el('id_platform').selectedOptions[0].textContent;
        const version=el('id_version').value+'.'+(el('id_build_number').value||'текущий выпуск');
        if(!confirm('Создать '+(all?'все клиенты':'клиент')+'?\nПлатформы: '+targets+'\nВерсия: '+version+'\nЗапросы будут отправлены в GitHub Actions. Публикация не выполняется.')){event.preventDefault();return;}
        if(form.dataset.submitting){event.preventDefault();return;}
        form.dataset.submitting='1';
        // Keep submitter name/value in the submitted form while preventing duplicate clicks.
        for(const button of [el('build-single'),el('build-all')])button.style.pointerEvents='none';
        if(form.dataset.local!=='true')return;
        event.preventDefault();
        const banner=el('build-dispatch-message'),message=el('build-dispatch-text');
        banner.hidden=false;message.className='';message.textContent='Отправляем запрос в GitHub Actions…';
        try{
            const body=new FormData(form);body.set('build_scope',all?'all':'single');
            const response=await fetch(form.action,{method:'POST',headers:{'X-Requested-With':'XMLHttpRequest','X-CSRFToken':body.get('csrfmiddlewaretoken')},body});
            const data=await response.json();
            if(!response.ok){
                const fields=Object.entries(data.fields||{});
                if(fields.length){const input=form.querySelector('[name="'+fields[0][0].replace(/[^a-zA-Z0-9_-]/g,'')+'"]');const page=input?.closest('[data-settings-panel]');if(page)window.rdgenConstructor.panel(page.dataset.settingsPanel);input?.focus();}
                throw Error([data.error,...fields.flatMap(([name,errors])=>errors.map(e=>name+': '+e.message))].filter(Boolean).join('\n'));
            }
            if(data.builds){
                const successful=data.builds.filter(b=>b.success).length;
                message.textContent='Запущено сборок: '+successful+' из '+data.builds.length+'.'+data.builds.filter(b=>!b.success).map(b=>' '+b.platform+': '+b.error).join('');
                message.className=successful===data.builds.length?'success':'error';
            }else{message.textContent='Сборка запущена: '+targets+' · '+(data.app_version||version)+'.';message.className='success';}
        }catch(error){message.className='error';message.textContent=error.message;}
        finally{delete form.dataset.submitting;for(const button of [el('build-single'),el('build-all')])button.style.pointerEvents='';}
    });
})();
