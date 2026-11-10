(() => {
    const body=document.getElementById('builds-table-body'),filter=document.getElementById('build-filter'),updated=document.getElementById('builds-updated');
    const names={windows:'Windows · 64 бита','windows-x86':'Windows · 32 бита',linux:'Linux',macos:'macOS',android:'Android APK'};
    const labels={queued:'В очереди',pending:'Ожидание запуска',waiting:'Ожидание',in_progress:'Собирается',run_not_found:'Ожидание запуска',cancelled:'Отменено',failure:'Ошибка сборки',timed_out:'Превышено время',dispatch_failed:'Ошибка запуска',action_required:'Требуется действие',skipped:'Пропущено'};
    let builds=[];
    function state(build){
        if(build.status==='completed'){
            if(build.conclusion!=='success')return {label:labels[build.conclusion]||build.conclusion||'Завершено',group:'error',style:'failed'};
            if(build.download_status==='completed')return {label:'Готово · скачано',group:'ready',style:'ready'};
            if(build.download_status==='error')return {label:'Ошибка скачивания',group:'error',style:'failed'};
            return {label:'Скачивается',group:'active',style:'running'};
        }
        return {label:labels[build.status]||build.status||'Ожидание',group:'active',style:build.status==='in_progress'?'running':''};
    }
    function duration(build){
        const start=Date.parse(build.started_at),end=build.status==='completed'?Date.parse(build.finished_at):Date.now();
        if(!Number.isFinite(start)||!Number.isFinite(end))return '—';
        const seconds=Math.max(0,Math.floor((end-start)/1000));return seconds<60?seconds+' с':Math.floor(seconds/60)+' мин';
    }
    function link(text,href){const a=document.createElement('a');a.textContent=text;a.href=href;return a;}
    function render(){
        body.replaceChildren();
        let active=0;
        for(const build of builds){
            const status=state(build);if(status.group==='active')active++;
            if(filter.value!=='all'&&filter.value!==status.group)continue;
            const tr=document.createElement('tr');
            for(const text of [names[build.platform]||build.platform,build.app_version||build.version||'—']){const td=document.createElement('td');td.textContent=text;tr.append(td);}
            const statusCell=document.createElement('td'),span=document.createElement('span');span.className='build-state '+status.style;span.textContent=status.label;statusCell.append(span);
            if(build.download_error){const error=document.createElement('div');error.className='small error';error.textContent=build.download_error;statusCell.append(error);}
            tr.append(statusCell);
            const time=document.createElement('td');time.textContent=duration(build);tr.append(time);
            const actions=document.createElement('td');actions.append(link('Подробности','/local-build/'+encodeURIComponent(build.id)));
            try{const url=new URL(build.log_url);if(url.protocol==='https:'&&url.hostname==='github.com'){const a=link('Журнал ↗',url.href);a.target='_blank';a.rel='noopener';actions.append(document.createTextNode(' · '),a);}}catch(_){}
            if(status.group==='ready')actions.append(document.createTextNode(' · '),link('К публикации','/desktop/publication'));
            if(build.download_status==='error'){
                const retry=document.createElement('button');retry.type='button';retry.textContent='Повторить скачивание';retry.className='secondary';retry.style.marginLeft='10px';
                retry.onclick=async()=>{retry.disabled=true;try{const r=await fetch('/desktop/retry',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':document.querySelector('[name=csrfmiddlewaretoken]').value},body:JSON.stringify({id:build.id})});if(!r.ok)throw Error('Не удалось повторить скачивание.');await refresh();}catch(e){updated.textContent=e.message;}finally{retry.disabled=false;}};actions.append(retry);
            }
            tr.append(actions);body.append(tr);
        }
        const badge=document.getElementById('active-build-count');badge.textContent=active;badge.hidden=!active;
        if(!body.children.length){const row=body.insertRow(),cell=row.insertCell();cell.colSpan=5;cell.textContent=builds.length?'Нет сборок с выбранным статусом.':'Сборок пока нет. Запустите создание клиента в конструкторе.';}
    }
    async function refresh(){const r=await fetch('/desktop/builds');if(!r.ok)throw Error('Не удалось получить статусы сборок.');builds=(await r.json()).builds;render();updated.textContent='Обновлено: '+new Date().toLocaleTimeString('ru-RU')+' · автоматически';}
    filter.onchange=render;
    async function poll(){try{await refresh();}catch(e){updated.textContent=e.message;}finally{setTimeout(poll,3000);}}
    poll();
})();
