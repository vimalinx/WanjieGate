import {esc,markdown,number} from './components.js';

function sparkline(quote) {
  const values=(quote.points||[]).map(p=>p.value).filter(Number.isFinite);
  if(values.length<2)return `<p class="quote-period">${esc(quote.chart_error||'暂无走势')}</p>`;
  const low=Math.min(...values),high=Math.max(...values),range=high-low||1;
  const points=values.map((v,i)=>`${(i/(values.length-1)*480).toFixed(2)},${(84-(v-low)/range*70).toFixed(2)}`).join(' ');
  return `<svg class="quote-chart" viewBox="0 0 480 100" role="img" aria-label="${esc(quote.name)}${esc(quote.period||'当日走势')}，最低${number(low)}，最高${number(high)}"><polyline points="${points}"/></svg><div class="quote-period"><span>${esc(quote.period||'当日走势')}</span><span>${number(low)} — ${number(high)}</span></div>`;
}

export function sceneSurfaces(scene) {
  if(!scene || scene.status==='loading')return [{key:'loading',span:12,className:'scene-loading',html:`<div class="scene-loading-line"><i></i><span>${esc(scene?.title||'正在理解并组合内容')}</span></div><div class="scene-skeleton"><i></i><i></i><i></i></div>`}];
  if(scene.status==='failed')return [{key:'failure',span:12,html:`<header class="live-heading">${esc(scene.title)}</header><p class="scene-error">${esc(scene.error)}</p>`}];
  const surfaces=[];
  (scene.blocks||[]).forEach((b,i)=>{
    if(b.type==='quotes') {
      for(const q of b.items) {
        const source=/^https:\/\/(?:gu\.qq\.com|finance\.yahoo\.com)\//.test(q.url) ? `<a href="${esc(q.url)}" target="_blank" rel="noopener noreferrer">${esc(q.source)} ↗</a>` : esc(q.source);
        surfaces.push({key:'quote:'+q.symbol,span:b.items.length===1?12:4,className:'quote-card',html:`<header class="quote-header"><h2>${esc(q.name)}</h2><span>${esc(q.symbol)}</span></header><div class="quote-price ${q.change>=0?'up':'down'}"><strong>${number(q.price)}</strong><span>${esc(q.currency)}</span></div><div class="quote-change ${q.change>=0?'up':'down'}">${q.change>=0?'+':''}${number(q.change)} <span>${q.percent>=0?'+':''}${number(q.percent)}%</span></div>${sparkline(q)}<footer class="quote-source">${source}<time datetime="${esc(q.asof)}">截至 ${esc(new Date(q.asof).toLocaleString('zh-CN',{hour12:false}))}</time></footer>`});
      }
      return;
    }
    let html=`<header class="live-heading"><span>${esc(b.title||scene.title||'')}</span></header>`;
    if(b.type==='text')html+=`<div class="markdown">${markdown(b.text)}</div>`;
    if(b.type==='tasks')html+=`<div class="live-tasks">${b.items.map((item,j)=>`<label><input type="checkbox" data-live-task="${i}:${j}"><span>${esc(item)}</span></label>`).join('')}</div>`;
    if(b.type==='choices')html+=`<div class="scene-choices">${b.items.map(item=>`<button data-scene-choice="${esc(item.value)}">${esc(item.label)} <span>↗</span></button>`).join('')}</div>`;
    if(b.type==='table')html+=`<div class="table-scroll"><table><thead><tr>${b.headers.map(h=>`<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${b.rows.map(row=>`<tr>${row.map(cell=>`<td>${esc(cell)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
    surfaces.push({key:`scene:${b.type}:${i}`,span:b.type==='tasks' && scene.blocks.length>1?5:b.type==='text' && scene.blocks.some(x=>x.type==='tasks')?7:12,html});
  });
  if(scene.source)surfaces.push({key:'source',span:12,className:'scene-source',html:`<span>${esc(scene.source)}</span>${scene.route==='market'?'<span>每 30 秒更新</span>':'<button class="quiet-button" data-scene-save>保存内容</button>'}`});
  return surfaces;
}

export function sceneText(scene) {
  return '# '+(scene.title||'内容')+'\n\n'+(scene.blocks||[]).map(b=>{
    if(b.type==='text')return b.text;
    if(b.type==='tasks')return b.items.map(x=>'- [ ] '+x).join('\n');
    if(b.type==='table')return [b.headers.join(' | '),...b.rows.map(r=>r.join(' | '))].join('\n');
    if(b.type==='choices')return b.title+'\n'+b.items.map(x=>x.label).join(' / ');
    return '';
  }).join('\n\n');
}
