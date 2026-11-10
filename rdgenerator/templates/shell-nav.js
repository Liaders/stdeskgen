(() => {
    if(window.chrome?.webview){
        const reload=document.querySelector('[data-native-reload]');reload.hidden=false;reload.onclick=()=>window.chrome.webview.postMessage({reload:true});
        const routes=new Set(['/','/desktop/builds-page','/desktop/publication']);
        document.addEventListener('click',event=>{const a=event.target.closest('a');if(!a)return;const url=new URL(a.href,location.href);if(url.origin===location.origin&&routes.has(url.pathname)){event.preventDefault();window.chrome.webview.postMessage({route:url.pathname});}});
    }
    if(document.getElementById('builds-table-body'))return;
    async function update(){
        try{const response=await fetch('/desktop/builds');if(!response.ok)return;const data=await response.json();const count=data.builds.filter(b=>b.status!=='completed'||(b.conclusion==='success'&&!['completed','error'].includes(b.download_status))).length;const badge=document.getElementById('active-build-count');if(badge){badge.hidden=!count;badge.textContent=count;}}
        catch(_){}finally{setTimeout(update,10000);}
    }
    update();
})();
