import {icon} from './icons.js';
export const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const number = n => new Intl.NumberFormat('zh-CN', {maximumFractionDigits: 2}).format(n);
export function markdown(text) {
  const lines = esc(text).split('\n'), output = [];
  for (let i = 0; i < lines.length; i++) {
    let line = lines[i];
    if (line.includes('|') && /^\s*\|?\s*:?-{3,}[-:|\s]*$/.test(lines[i+1] || '')) {
      const cells = row => row.trim().replace(/^\||\|$/g,'').split('|').map(c=>c.trim());
      const header = cells(line); i += 2;
      const body = [];
      while (i < lines.length && lines[i].includes('|') && lines[i].trim()) {body.push(cells(lines[i])); i++;}
      i--;
      output.push(`<div class="table-scroll" tabindex="0"><table><thead><tr>${header.map(c=>`<th>${c}</th>`).join('')}</tr></thead><tbody>${body.map(row=>`<tr>${row.map(c=>`<td>${c}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`);
      continue;
    }
    line = line.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/`([^`]+)`/g, '<code>$1</code>');
    if (/^### /.test(line)) output.push(`<h4>${line.slice(4)}</h4>`);
    else if (/^## /.test(line)) output.push(`<h3>${line.slice(3)}</h3>`);
    else if (/^# /.test(line)) output.push(`<h2>${line.slice(2)}</h2>`);
    else if (/^[-*] /.test(line)) output.push(`<p class="md-bullet">${line.slice(2)}</p>`);
    else output.push(line.trim() ? `<p>${line}</p>` : '<div class="md-space"></div>');
  }
  return output.join('');
}
export function descriptors(artifacts, registry) {
  return artifacts.flatMap(a => Object.entries(registry.components).filter(([key, c]) => c.accepts === a.type && (!a.components || a.components.includes(key))).map(([component, c]) => ({key:a.id + ':' + component, component, spec:c, artifact:a})))
    .sort((a, b) => Number(b.artifact.pinned) - Number(a.artifact.pinned) || a.artifact.created - b.artifact.created);
}
function head(d, title, sub) {
  const a = d.artifact;
  if (a.transient) return `<header class="card-header"><div><span class="card-kicker">${esc(sub || d.spec.label)}</span><h3>${esc(title)}</h3></div></header>`;
  return `<header class="card-header"><div><span class="card-kicker">${esc(sub || d.spec.label)}</span><h3>${esc(title)}</h3></div><button class="icon-button pin-button ${a.pinned ? 'is-pinned' : ''}" data-action="pin" data-id="${a.id}" aria-label="${a.pinned ? '取消固定' : '固定'}${esc(title)}" aria-pressed="${a.pinned}">${icon('pin')}</button></header>`;
}
function source(a) {return `<footer class="card-footer"><span><i class="small-dot"></i>${a.data.dataset?.demo ? '演示数据 · ' : ''}${esc(a.source)}</span><span>${a.transient ? '未保存' : '已保存'}</span></footer>`;}
function chart(data, index = 0) {
  const col = data.columns[index] || data.columns[0], values = col.values;
  const min = Math.min(...values, 0), max = Math.max(...values, 0), range = max - min || 1;
  const x = i => 25 + i / Math.max(1, values.length - 1) * 750, y = n => 165 - (n - min) / range * 140;
  const points = values.map((v, i) => `${x(i)},${y(v)}`).join(' ');
  const ticks = [0,.5,1].map(t => {const v = min + t * range; return `<line x1="25" x2="775" y1="${y(v)}" y2="${y(v)}"/><text x="25" y="${y(v)-7}">${esc(number(v))}</text>`;}).join('');
  return `<svg class="trend-chart" viewBox="0 0 800 215" role="img" aria-label="${esc(col.name)}趋势，${values.length}个数据点"><g class="chart-grid">${ticks}</g><polygon points="25,165 ${points} 775,165" class="chart-area"/><polyline points="${points}" class="chart-line"/>${values.length <= 32 ? values.map((v,i) => `<circle cx="${x(i)}" cy="${y(v)}" r="3.5"><title>${esc(data.labels[i])}：${esc(number(v))}</title></circle>`).join('') : ''}<g class="chart-labels"><text x="25" y="201">${esc(data.labels[0])}</text><text x="775" y="201" text-anchor="end">${esc(data.labels.at(-1))}</text></g></svg>`;
}
export function renderComponent(d) {
  const a = d.artifact, data = a.data;
  switch (d.component) {
    case 'metrics': {
      const c = data.columns[0];
      return `<div class="metrics-meta"><span>${esc(a.title)}</span><span>${data.dataset.demo ? '演示数据 · ' : ''}本地计算 · ${data.count} 条记录</span></div><div class="metrics-grid">${[['合计 · '+c.name,number(c.total),'所选数值列的总和'],['平均值',number(c.mean),'每条记录的平均'],['首尾变化',c.change === null ? '—' : (c.change > 0 ? '+' : '')+number(c.change)+'%','末值相对首值，不代表环比']].map(([title,val,hint]) => `<div><span>${esc(title)}</span><strong>${esc(val)}</strong><small>${esc(hint)}</small></div>`).join('')}</div>`;
    }
    case 'chart': return head(d,'看见变化',data.columns[0].name)+`<div class="chart-select"><label>指标 <select data-action="chart-column" aria-label="图表指标">${data.columns.map((c,i) => `<option value="${i}">${esc(c.name)}</option>`).join('')}</select></label><span>${data.count} 个数据点</span></div><div class="chart-container">${chart(data)}</div><details class="inline-details"><summary>查看原始明细</summary><div class="table-scroll" tabindex="0"><table><thead><tr>${data.dataset.headers.map(h=>`<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${data.dataset.rows.map(r=>`<tr>${r.map(v=>`<td>${esc(v)}</td>`).join('')}</tr>`).join('')}</tbody></table></div></details>`+source(a);
    case 'table': return head(d,'每一个细节',a.title)+`<div class="table-scroll" tabindex="0" aria-label="可滚动数据明细"><table><thead><tr>${data.dataset.headers.map(h => `<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${data.dataset.rows.map(r => `<tr>${r.map(v => `<td>${esc(v)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`+source(a);
    case 'document': return head(d,a.title,'文字，让想法清晰')+`<div class="document-body markdown">${markdown(data.text)}</div><textarea class="document-editor" aria-label="编辑${esc(a.title)}" hidden>${esc(data.text)}</textarea><div class="document-actions"><button class="quiet-button" data-action="edit">${icon('note')}编辑文稿</button><button class="primary-button" data-action="save" hidden>保存修改</button><button class="quiet-button" data-action="discard" hidden>放弃修改</button><span class="edit-state"></span></div>`+source(a);
    case 'tasks': {const done = data.items.filter(t => t.done).length; return head(d,a.title,'从想法到行动')+`<div class="task-progress"><span>${done} / ${data.items.length} 已完成</span><div><i style="width:${done/data.items.length*100}%"></i></div></div><div class="task-list">${data.items.map(t => `<label class="task-item ${t.done ? 'done' : ''}"><input type="checkbox" data-action="task" data-task="${t.id}" ${t.done ? 'checked' : ''}><span><strong>${esc(t.title)}</strong><small>${esc(t.detail)}</small></span></label>`).join('')}</div>`+source(a);}
  }
}
export function updateChart(card, data, index) {card.querySelector('.chart-container').innerHTML = chart(data,index);}
