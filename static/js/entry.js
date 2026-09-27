const demo=new URLSearchParams(location.search).get('demo')==='1';
import(demo?'./demo-runtime.js':'../runtime-app.js').catch(error=>{const notice=document.querySelector('#toast');notice.textContent='页面加载失败：'+error.message;notice.hidden=false;});
