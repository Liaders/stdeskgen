(() => {
    const list = document.getElementById('recent-build-list');
    if (!list) return;
    const labels = {queued:'В очереди',in_progress:'Собирается',pending:'Ожидание запуска',waiting:'Ожидание',success:'Успешно',failure:'Ошибка',cancelled:'Отменено',completed:'Завершена',dispatch_failed:'Ошибка запуска',run_not_found:'Запуск пока не найден на GitHub'};
    async function refresh() {
        try {
            const r = await fetch('/desktop/builds');
            if (!r.ok) return;
            const data = await r.json();
            list.replaceChildren();
            for (const build of data.builds) {
                const p = document.createElement('p'), a = document.createElement('a');
                a.href = '/local-build/' + build.id;
                a.textContent = build.filename || build.id;
                const state = build.status === 'completed' ? build.conclusion : build.status;
                const ru = document.getElementById('constructor-language')?.value !== 'en';
                p.append(a, document.createTextNode(' — ' + (ru ? labels[state] || state : state)));
                if (build.download_status === 'completed') p.append(document.createTextNode(ru ? ' · скачано на компьютер' : ' · downloaded locally'));
                else if (build.download_status === 'error') {
                    p.append(document.createTextNode(' · ' + build.download_error));
                    const retry = document.createElement('button'); retry.type='button'; retry.textContent=ru?'Повторить скачивание':'Retry download';
                    retry.onclick = async () => {await fetch('/desktop/retry',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':document.querySelector('[name=csrfmiddlewaretoken]').value},body:JSON.stringify({id:build.id})});retry.disabled=true;};
                    p.append(retry);
                } else if (state === 'success') p.append(document.createTextNode(ru ? ' · скачиваем артефакты…' : ' · downloading artifacts…'));
                list.append(p);
            }
        } finally {setTimeout(refresh, 3000);}
    }
    refresh().catch(()=>{});
})();
