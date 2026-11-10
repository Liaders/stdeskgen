(() => {
    if(window.chrome?.webview){
        document.querySelector('.app-header nav').hidden=true;
        const routes={'/':0,'/desktop/builds-page':1,'/desktop/publication':2};
        document.addEventListener('click',event=>{const a=event.target.closest('a');if(!a)return;const url=new URL(a.href,location.href);if(url.origin===location.origin&&url.pathname in routes){event.preventDefault();window.chrome.webview.postMessage({tab:routes[url.pathname]});}});
        window.rdgenNativeCount=count=>window.chrome.webview.postMessage({buildCount:count});
    }
    if(document.getElementById('builds-table-body'))return;
    async function update(){
        try{const response=await fetch('/desktop/builds');if(!response.ok)return;const data=await response.json();const count=data.builds.filter(b=>b.status!=='completed'||(b.conclusion==='success'&&!['completed','error'].includes(b.download_status))).length;const badge=document.getElementById('active-build-count');if(badge){badge.hidden=!count;badge.textContent=count;}window.rdgenNativeCount?.(count);}
        catch(_){}finally{setTimeout(update,10000);}
    }
    update();
})();
