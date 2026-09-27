import {esc, renderComponent} from './components.js';

// Local data can render immediately; text and plans come from the live runtime.
export function liveSurfaces(plan, components, text, analysis) {
  const result = [];
  if (plan.steps.some(s=>s.id==='analyze')) {
    if (!analysis) result.push({key:'data',span:12,html:'<button class="live-import" data-live="import">＋ 添加要分析的数据</button>'});
    else for (const c of components.filter(c=>c.accepts==='analysis')) {
      const artifact={id:'live-analysis',title:analysis.dataset.name,type:'analysis',data:analysis,transient:true,source:'实时计算'};
      result.push({key:c.id,span:c.span,html:renderComponent({component:c.id,spec:c,artifact})});
    }
  }
  return result;
}

export function renderLiveSurface(container, surfaces) {
  const keys=new Set(surfaces.map(s=>s.key));
  for (const el of [...container.children]) if (!keys.has(el.dataset.liveKey)) {
    if (el.contains(document.activeElement)) document.querySelector('#input').focus();
    el.remove();
  }
  surfaces.forEach((s,i)=>{
    let el=[...container.children].find(el=>el.dataset.liveKey===s.key);
    if (!el) {el=document.createElement('article'); el.className='live-card'; el.dataset.liveKey=s.key; container.append(el);}
    el.className='live-card '+(s.className||'');
    el.style.setProperty('--span',s.span); el.style.order=i;
    // Do not replace the focused editor or reset task toggles on identical KEV results.
    if (el._markup!==s.html) {
      const editor=el.querySelector('.live-editor'), focused=editor===document.activeElement;
      const checked=new Set([...el.querySelectorAll('.live-tasks input:checked')].map(x=>x.nextElementSibling.textContent));
      if (focused) {el._markup=s.html; return;}
      el.innerHTML=s.html; el._markup=s.html;
      for (const item of el.querySelectorAll('.live-tasks input')) item.checked=checked.has(item.nextElementSibling.textContent);
    }
  });
}
