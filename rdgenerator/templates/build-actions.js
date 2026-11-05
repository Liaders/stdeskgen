(() => {
    const el=id=>document.getElementById(id), form=el('myForm');
    form.addEventListener('submit',event=>{
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
    });
})();
