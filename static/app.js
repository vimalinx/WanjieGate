import {api, workspacePath} from './js/api.js';
import {infer, planFrom, selectComponents} from './js/composition.js';
import {descriptors, renderComponent, updateChart, esc} from './js/components.js';
import {icon, hydrateIcons} from './js/icons.js';
import {LivePreview} from './js/live-preview.js';
import {liveSurfaces, renderLiveSurface} from './js/live-surface.js';
import {sceneSurfaces, sceneText} from './js/scene.js';

const $ = selector => document.querySelector(selector);
const input = $('#input');
const state = {registry:null, workspace:null, plan:null, scores:{}, override:null, previewIds:[], analysis:null, scene:null, sceneRevision:0, scenePoll:null, client:crypto.randomUUID(), composing:false, submitting:false, job:null, poll:null, view:'canvas', dirty:new Set(), routeSeq:0};
const terminal = new Set(['complete','failed','cancelled','interrupted']);
let toastTimer;
const cacheKey = (kind,id) => `wanjie:${kind}:${id}`;
function cached(kind,id) {try {return JSON.parse(sessionStorage.getItem(cacheKey(kind,id)) || 'null');} catch {return null;}}
function cache(kind,id,value) {try {if (value === null) sessionStorage.removeItem(cacheKey(kind,id)); else sessionStorage.setItem(cacheKey(kind,id),JSON.stringify(value));} catch {}}
function toast(message) {$('#toast').textContent = message; $('#toast').hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => $('#toast').hidden = true,5500);}
function fail(error) {toast(error.message || String(error));}
function busy() {return state.submitting || (state.job && !terminal.has(state.job.status));}
function resizeInput() {input.style.height = 'auto'; input.style.height = Math.min(240,Math.max(28,input.scrollHeight))+'px';}
const blankWorkspace = () => ({id:null,title:'新的空间',artifacts:[],messages:[],jobs:[],dataset:null});
let creatingWorkspace = null;
async function ensureWorkspace() {
  if (state.workspace.id) return state.workspace.id;
  if (!creatingWorkspace) creatingWorkspace = api('/workspaces',{}).then(w => {
    state.workspace = w;
    history.replaceState({},'','/w/'+w.id);
    cache('draft',w.id,input.value);
    return w.id;
  }).finally(() => {creatingWorkspace = null;});
  return creatingWorkspace;
}
function renderEntrance() {
  const active = !!(input.value.trim() || state.workspace?.dataset || state.workspace?.artifacts.length || state.workspace?.messages.length || state.job);
  document.body.classList.toggle('entered',active);
  $('#composer-context').hidden = !active;
}
for (let i=0;i<12;i++) {
  const strip = document.createElement('div'); strip.className = 'shutter';
  strip.style.setProperty('--i',i); strip.style.setProperty('--direction',i%2 ? 1 : -1);
  const word = document.createElement('span'); word.textContent = 'WanJie'; strip.append(word);
  $('#entrance').append(strip);
}
const livePreview = new LivePreview(
  payload => api('/preview',payload),
  result => {
    state.scores = result.scores;
    state.analysis = result.analysis || state.analysis;
    state.scene = result.scene;
    if (state.scene?.status === 'loading') pollScene(state.sceneRevision);
    else scheduleSceneRefresh(state.sceneRevision);
    $('#decision-status').textContent = result.decision.source.startsWith('kev') ? '实时理解' : '本地预览';
    $('#decision-status').title = result.decision.reason || `KEV · ${result.decision.latency_ms} ms`;
    renderPreview();
  },
  (label,error) => {$('#decision-status').textContent = label; if(error) {state.scene={status:'failed',title:'连接暂不可用',error:'无法获取新的界面内容，请稍后修改输入重试。'};renderLive();}}
);
function invalidatePreview() {livePreview.clear(); state.sceneRevision++; clearTimeout(state.scenePoll); state.scene=null;}
function cancelScene() {api('/scenes/'+state.client+'/cancel',{revision:state.sceneRevision}).catch(()=>{});}
function scheduleSceneRefresh(revision) {
  clearTimeout(state.scenePoll);
  if (state.scene?.status==='ready' && state.scene.route==='market') state.scenePoll=setTimeout(()=>{
    if(revision===state.sceneRevision && input.value.trim()) onInput();
  },30000);
}
async function pollScene(revision) {
  clearTimeout(state.scenePoll);
  try {
    const scene=await api('/scenes/'+state.client+'/'+revision);
    if(revision!==state.sceneRevision)return;
    state.scene=scene;renderLive();
    if(scene.status==='loading')state.scenePoll=setTimeout(()=>pollScene(revision),350);
    else scheduleSceneRefresh(revision);
  } catch(e) {
    if(revision!==state.sceneRevision)return;
    state.scene={status:'failed',title:'连接中断',error:'无法读取内容状态；不会重复发起生成。'};renderLive();
  }
}
function renderLive() {
  const el = $('#live-surface');
  el.hidden = !input.value.trim() || !state.plan;
  document.body.classList.toggle('scene-busy',!el.hidden && (!state.scene || state.scene.status==='loading'));
  if (el.hidden) {el.replaceChildren(); return;}
  if (state.scene?.route !== 'data') {renderLiveSurface(el,sceneSurfaces(state.scene)); return;}
  const components = state.previewIds.map(id=>({id,...state.registry.components[id]}));
  renderLiveSurface(el,liveSurfaces(state.plan,components,input.value,state.analysis));
}
async function refreshList() {
  const {workspaces} = await api('/workspaces');
  $('#space-count').textContent = workspaces.length;
  $('#workspace-list').innerHTML = workspaces.map(w => `<a href="/w/${w.id}" class="workspace-link ${w.id === state.workspace?.id ? 'active' : ''}" data-workspace="${w.id}">${icon('space')}<span>${esc(w.title)}</span>${w.count ? `<small>${w.count}</small>` : ''}</a>`).join('');
}
function routePath() {return location.pathname.match(/^\/w\/([a-f0-9]{32})$/)?.[1];}
async function openWorkspace(id,push = true) {
  if (state.dirty.size) {toast('文稿还有未保存的修改，请先保存或放弃。'); return false;}
  if (state.submitting || creatingWorkspace) {toast('正在发送，请稍候。'); return false;}
  const routeSeq = ++state.routeSeq;
  invalidatePreview(); cancelScene(); clearTimeout(state.poll);
  const w = id ? await api(workspacePath(id)) : blankWorkspace();
  if (routeSeq !== state.routeSeq) return false;
  state.workspace = w; state.job = w.jobs?.[0] || null; state.override = null; state.plan = null; state.previewIds = []; state.analysis = null; $('#live-surface').replaceChildren();
  input.value = w.id ? cached('draft',w.id) || '' : ''; $('#canvas').replaceChildren();
  state.scores = infer(input.value,state.registry);
  const pending = cached('pending',w.id);
  if (pending) {const recovered = await api('/submissions/'+pending.request_id); if (routeSeq !== state.routeSeq) return false; if (recovered.job) {state.job = recovered.job; input.value = ''; cache('pending',w.id,null); cache('draft',w.id,null);}}
  const path = w.id ? '/w/'+w.id : '/';
  if (push) history.pushState({},'',path); else history.replaceState({},'',path);
  setView('canvas'); $('#routing-details').open = false;
  renderWorkspace(); renderPreview(); renderJob(); await refreshList();
  $('#sidebar').close();
  if (state.job && !terminal.has(state.job.status)) pollJob(state.job.id,w.id);
  if(input.value.trim())onInput();
  return true;
}
function renderWorkspace() {
  const w = state.workspace;
  const positions = new Map([...$('#canvas').children].map(el=>[el,el.getBoundingClientRect()]));
  $('#workspace-title').textContent = w.title;
  const hasWork = !!(w.artifacts.length || w.messages.length || state.job);
  document.body.classList.toggle('has-work',hasWork);
  $('#work-area').hidden = !hasWork; renderEntrance();
  $('#export-button').disabled = !w.artifacts.length;
  $('#attachments').innerHTML = w.dataset ? `<div class="attachment-chip">${icon('table')}<span>${esc(w.dataset.name)}</span><small>${w.dataset.rows.length} 行${w.dataset.demo ? ' · 演示数据' : ' · 本机'}</small><button class="icon-button" id="remove-data" aria-label="移除当前数据">${icon('close')}</button></div>` : '';
  const wanted = new Set();
  for (const d of descriptors(w.artifacts,state.registry)) {
    wanted.add(d.key);
    let card = [...$('#canvas').children].find(c => c.dataset.key === d.key);
    if (!card) {card = document.createElement('article'); card.className = 'artifact-card '+d.component; card.dataset.key = d.key; card.dataset.artifact = d.artifact.id; card.style.setProperty('--span',d.spec.span); $('#canvas').append(card);}
    const version = String(d.artifact.version);
    if (card.dataset.version !== version && !state.dirty.has(d.artifact.id)) {card.innerHTML = renderComponent(d); card.dataset.version = version;}
    card.classList.toggle('pinned',d.artifact.pinned);
    card.style.order = d.artifact.pinned ? -1 : 0;
    card.style.setProperty('--span', d.component === 'document' || (d.component === 'tasks' && !w.artifacts.some(a=>a.type==='analysis')) ? 12 : d.spec.span);
  }
  for (const card of $('#canvas').children) if (!wanted.has(card.dataset.key)) card.remove();
  if (!matchMedia('(prefers-reduced-motion: reduce)').matches && !state.dirty.size) for (const [el,old] of positions) {if (!el.isConnected) continue; const next=el.getBoundingClientRect(), dx=old.x-next.x, dy=old.y-next.y; if (dx || dy) el.animate([{transform:`translate(${dx}px,${dy}px)`},{transform:'none'}],{duration:320,easing:'cubic-bezier(.2,.7,.2,1)'});}
  renderHistory(); resizeInput();
}
function renderHistory() {
  const jobs = state.workspace.jobs || [];
  $('#history').innerHTML = jobs.length ? jobs.map(j => `<article class="history-entry"><div><span>${icon('clock')}${new Date(j.created*1000).toLocaleString('zh-CN')}</span><b>${statusLabel(j.status)}</b></div><h3>${esc(j.text)}</h3><ol>${j.events.map(e => `<li class="event-${e.status}">${esc(e.text)}</li>`).join('')}</ol></article>`).join('') : '<p class="empty-message">发送一个想法，执行过程会留在这里。</p>';
}
function statusLabel(s) {return ({queued:'等待执行',running:'正在执行',complete:'已完成',failed:'未完成',cancelled:'已停止',interrupted:'已中断'})[s] || s;}
function renderJob() {
  const j = state.job, el = $('#job-banner'); el.hidden = !j;
  if (j) {el.className = 'job-banner '+j.status; el.innerHTML = `<div><span class="job-indicator"></span><strong>${statusLabel(j.status)}</strong><span>${esc(j.error || j.events.at(-1)?.text || '')}</span></div>${!terminal.has(j.status) && !j.cancel_requested ? '<button class="quiet-button" id="cancel-job">停止</button>' : ''}<div class="execution-route">${j.plan.steps.map((s,i) => {const done=j.events.some(e=>e.status==='step-complete' && j.events.some(r=>r.step===s.id && r.seq===e.seq-1)); return `${i ? '<span>→</span>' : ''}<span class="${done ? 'done' : j.current===s.id ? 'current' : ''}">${done ? '✓ ' : ''}${esc(s.label)}</span>`;}).join('')}</div>`;}
  $('#send-button').disabled = !input.value.trim() || busy() || !!state.plan?.needs_data || ($('#local-only').checked && state.plan?.cloud);
  $('#send-button span:first-child').textContent = busy() ? '进行中' : '生成内容';
}
function renderPreview() {
  const text = input.value.trim();
  renderEntrance();
  $('#composition').hidden = !text;
  if (!text) {$('#send-scope').textContent = $('#local-only').checked ? '仅本地：计算与笔记，不发送到云端。' : '输入会自动获取或生成内容。'; $('#key-hint').textContent = 'Enter 换行 · Ctrl Enter 生成内容';}
  if (!text) {state.plan = null; $('#decision-status').textContent = ''; $('#composer').dataset.mode = 'answer'; renderLive(); renderJob(); resizeInput(); return;}
  state.plan = planFrom(state.scores,state.registry,!!state.workspace?.dataset,state.override);
  const plan = state.plan;
  $('#composer').dataset.mode = plan.mode;
  $('#plan-steps').innerHTML = plan.steps.map((s,i) => `${i ? '<span class="step-arrow">→</span>' : ''}<button class="plan-step ${s.blocked ? 'blocked' : ''}" data-capability="${s.id}" title="点击移除此能力"><span class="step-number">0${i+1}</span>${esc(s.label)}<small>${s.cost === 'local' ? '本地' : '模型'}</small><span class="step-remove">×</span></button>`).join('')+`<button class="add-capability" id="add-capability" aria-label="添加能力">${icon('plus')}</button>`;
  $('#plan-notice').hidden = true; // The live data surface owns the import action.
  $('#plan-notice').textContent = plan.needs_data ? '＋ 添加要分析的数据' : '';
  const components = selectComponents(plan,state.registry,state.previewIds);
  state.previewIds = components.map(c => c.id);
  const visibleComponents=state.scene?.route==='market' ? [{label:'行情'}] : components;
  $('#component-preview').innerHTML = visibleComponents.map(c => `<span class="preview-token">${esc(c.label)}</span>`).join('<span class="preview-separator">·</span>');
  $('#send-scope').textContent = $('#local-only').checked ? '仅本地：计算与笔记，不发送到云端。' : plan.cloud ? '输入与关联内容会自动交给模型生成界面内容。' : '这次在本机计算，不调用云端模型。';
  $('#key-hint').textContent = 'Enter 换行 · Ctrl Enter 生成内容';
  renderLive(); renderJob(); resizeInput();
}
function onInput() {
  if (!state.registry || !state.workspace) return;
  invalidatePreview(); state.override = null;
  if (state.workspace.id) cache('draft',state.workspace.id,input.value);
  state.scores = infer(input.value,state.registry); renderPreview();
  if (!input.value.trim()) {cancelScene();return;}
  if (state.composing) return;
  // Dispatch immediately. While KEV is running, retain only the newest input.
  livePreview.update({workspace:state.workspace.id,text:input.value,client:state.client,revision:state.sceneRevision,local_only:$('#local-only').checked});
}

async function submit() {
  if (busy() || !input.value.trim()) return;
  if (state.dirty.size) return toast('请先保存正在编辑的文稿，让新任务使用最新内容。');
  if (state.plan?.needs_data) return toast('请先添加数据。');
  if ($('#local-only').checked && state.plan?.cloud) return toast('仅本地模式不会调用云端模型。');
  const text = input.value.trim();
  const selected = state.plan.steps.map(s => s.id);
  const payload = {text,selected,local_only:$('#local-only').checked};
  invalidatePreview(); state.submitting = true; input.disabled = true; renderJob();
  let workspace;
  try {
    workspace = await ensureWorkspace();
    let attempt = cached('pending',workspace);
    if (attempt && JSON.stringify(attempt.payload) !== JSON.stringify(payload)) return toast('上次发送状态待确认。请刷新恢复状态后再发送不同内容。');
    if (!attempt) {attempt = {payload,request_id:crypto.randomUUID()}; cache('pending',workspace,attempt);}
    const job = await api(workspacePath(workspace)+'/jobs',{...payload,request_id:attempt.request_id});
    if (state.workspace.id !== workspace) return;
    state.job = job; input.value = ''; state.override = null; cache('pending',workspace,null); cache('draft',workspace,null);
    state.workspace = await api(workspacePath(workspace)); renderWorkspace(); renderPreview(); renderJob();
    refreshList().catch(fail); pollJob(job.id,workspace);
  } catch(e) {if (e.confirmedFailure) cache('pending',workspace,null); fail(e);} finally {state.submitting = false; input.disabled = false; renderJob();}
}
async function pollJob(id,workspace) {
  clearTimeout(state.poll);
  try {
    const job = await api('/jobs/'+id);
    if (state.workspace.id !== workspace) return;
    const changed = state.job?.events.length !== job.events.length;
    state.job = job; renderJob();
    if (changed || terminal.has(job.status)) {
      const w = await api(workspacePath(workspace));
      if (state.workspace.id !== workspace) return;
      state.workspace = w; renderWorkspace();
    }
    if (terminal.has(job.status)) {refreshList().catch(fail); return;}
  } catch(e) {if (state.workspace.id !== workspace) return; $('#job-banner').textContent = '连接中断，正在恢复执行状态；不会重复发送。';}
  state.poll = setTimeout(() => pollJob(id,workspace),800);
}
async function mutateArtifact(id,patch) {
  const workspace = state.workspace.id, a = state.workspace.artifacts.find(a => a.id === id);
  const w = await api(workspacePath(workspace)+'/artifacts/'+id,{version:a.version,...patch},{method:'PATCH'});
  if (state.workspace.id !== workspace) return;
  state.workspace = {...w,jobs:state.workspace.jobs}; renderWorkspace();
}
async function addData(text,name,demo = false) {
  const workspace = await ensureWorkspace();
  const w = await api(workspacePath(workspace)+'/dataset',{text,name,demo});
  if (state.workspace.id !== workspace) return;
  state.workspace = {...w,jobs:state.workspace.jobs}; state.analysis = null; renderWorkspace(); onInput();
}
function showInfo(title,html) {$('#info-title').textContent = title; $('#info-content').innerHTML = html; $('#info-dialog').showModal();}
function setView(view) {state.view = view; $('#canvas').hidden = view !== 'canvas'; $('#history').hidden = view !== 'history'; $('#view-canvas').classList.toggle('active',view === 'canvas'); $('#view-history').classList.toggle('active',view === 'history');}

hydrateIcons();
input.addEventListener('input',onInput);
input.addEventListener('compositionstart',() => {state.composing = true; invalidatePreview();});
input.addEventListener('compositionend',() => {state.composing = false; onInput();});
input.addEventListener('keydown',e => {if (e.key === 'Enter' && !e.isComposing && !state.composing && (e.ctrlKey || e.metaKey)) {e.preventDefault(); submit();}});
$('#send-button').addEventListener('click',submit);
$('#live-surface').addEventListener('click',async e => {
  if (e.target.closest('[data-live=import]')) $('#attach-button').click();
  const choice=e.target.closest('[data-scene-choice]');
  if(choice){input.value=choice.dataset.sceneChoice; input.focus();onInput();}
  if(e.target.closest('[data-scene-save]') && state.scene?.status==='ready') {
    const text=sceneText(state.scene);
    try {const workspace=await ensureWorkspace(); await api(workspacePath(workspace)+'/note',{text}); state.workspace=await api(workspacePath(workspace));renderWorkspace();refreshList().catch(fail);toast('内容已保存');} catch(error){fail(error);}
  }
});
$('#live-surface').addEventListener('change',e => {
  if (e.target.dataset.action === 'chart-column' && state.analysis) updateChart(e.target.closest('.live-card'),state.analysis,Number(e.target.value));
});
$('#new-space').addEventListener('click',() => openWorkspace().catch(fail));
$('#menu-button').addEventListener('click',() => {refreshList().catch(fail); $('#sidebar').showModal();});
$('#sidebar').addEventListener('click',e => {if (e.target === $('#sidebar')) {const r=e.target.getBoundingClientRect(); if (e.clientX<r.left || e.clientX>r.right || e.clientY<r.top || e.clientY>r.bottom) e.target.close();}});
$('#plan-notice').addEventListener('click',() => $('#attach-button').click());
$('#local-only').addEventListener('change',onInput);
$('#attach-button').addEventListener('click',() => {$('#data-error').textContent = ''; $('#data-dialog').showModal();});
$('#import-button').addEventListener('click',async () => {try {await addData($('#data-text').value,$('#data-name').value); $('#data-dialog').close(); toast('数据已添加到本机空间');} catch(e) {$('#data-error').textContent = e.message;}});
$('#data-file').addEventListener('change',async e => {const file = e.target.files[0]; if (!file) return; if (file.size > 100000) {$('#data-error').textContent = '文件需小于 100 KB'; return;} $('#data-text').value = await file.text(); $('#data-name').value = file.name;});
$('#note-button').addEventListener('click',async () => {if (!input.value.trim()) return toast('先写一点内容，再存为笔记。'); try {const workspace = await ensureWorkspace(); await api(workspacePath(workspace)+'/note',{text:input.value}); if (state.workspace.id !== workspace) return; input.value = ''; cache('draft',workspace,null); state.workspace = await api(workspacePath(workspace)); renderWorkspace(); onInput(); refreshList().catch(fail); toast('笔记已保存在本机');} catch(e) {fail(e);}});
$('#export-button').addEventListener('click',async () => {if (state.dirty.size) return toast('请先保存文稿修改，再导出。'); try {const data = await api(workspacePath(state.workspace.id)+'/export'); const url = URL.createObjectURL(new Blob([data.text],{type:'text/markdown;charset=utf-8'})); const a = document.createElement('a'); a.href = url; a.download = data.filename; a.click(); setTimeout(() => URL.revokeObjectURL(url),1000);} catch(e) {fail(e);}});
$('#view-canvas').addEventListener('click',() => setView('canvas'));
$('#view-history').addEventListener('click',() => setView('history'));
$('#status-button').addEventListener('click',async () => {try {const s = await api('/status'); showInfo('连接与执行',`<p class="dialog-desc">只有实际调用成功，才标记为已验证。模型请求失败时保留回执，不自动重试。</p><dl class="connection-list"><dt>本地工作区</dt><dd>已连接 · SQLite 持久保存</dd><dt>意图判断 · KEV</dt><dd>${esc(s.kev.state)}${s.kev.latency_ms ? ' · '+s.kev.latency_ms+' ms' : ''}</dd><dt>内容生成</dt><dd>${esc(s.generator.pack)} / ${esc(s.generator.model)}<br>${esc(s.generator.state)}${s.generator.latency_ms ? ' · '+s.generator.latency_ms+' ms' : ''}</dd><dt>执行队列</dt><dd>${s.active_jobs} 个任务 · 最多 2 个并发</dd></dl>`);} catch(e) {fail(e);}});
document.addEventListener('click',async e => {
  const link = e.target.closest('[data-workspace]');
  if (link) {e.preventDefault(); try {await openWorkspace(link.dataset.workspace);} catch(e) {fail(e);} return;}
  const cap = e.target.closest('[data-capability]');
  if (cap) {state.override = state.plan.steps.map(s => s.id).filter(k => k !== cap.dataset.capability); renderPreview(); return;}
  if (e.target.closest('#add-capability')) {showInfo('加入一个能力',`<div class="capability-picker">${Object.entries(state.registry.capabilities).map(([k,c]) => `<button data-add-capability="${k}">${esc(c.label)}<span>${c.cost === 'local' ? '本地' : '云端'} ＋</span></button>`).join('')}</div>`); return;}
  const add = e.target.closest('[data-add-capability]'); if (add) {state.override = [...new Set([...state.plan.steps.map(s => s.id),add.dataset.addCapability])]; $('#info-dialog').close(); renderPreview(); return;}
  if (e.target.closest('#cancel-job')) {try {state.job = await api('/jobs/'+state.job.id+'/cancel',{}); renderJob();} catch(e) {fail(e);} return;}
  if (e.target.closest('#remove-data')) {try {const w = await api(workspacePath(state.workspace.id)+'/dataset',{remove:true}); state.workspace = {...w,jobs:state.workspace.jobs}; state.analysis = null; renderWorkspace(); onInput();} catch(e) {fail(e);} return;}
  const button = e.target.closest('[data-action]'), card = button?.closest('.artifact-card');
  if (!button || !card) return;
  const id = card.dataset.artifact, artifact = state.workspace.artifacts.find(a => a.id === id);
  try {
    if (button.dataset.action === 'pin') {if (state.dirty.has(id)) return toast('请先保存文稿。'); await mutateArtifact(id,{pinned:!artifact.pinned});}
    if (button.dataset.action === 'edit') {state.dirty.add(id); card.querySelector('.document-body').hidden = true; card.querySelector('.document-editor').hidden = false; card.querySelector('[data-action="edit"]').hidden = true; card.querySelector('[data-action="save"]').hidden = false; card.querySelector('[data-action="discard"]').hidden = false; card.querySelector('.document-editor').focus();}
    if (button.dataset.action === 'save') {button.disabled = true; const text = card.querySelector('.document-editor').value; await mutateArtifact(id,{text}); state.dirty.delete(id); card.dataset.version = ''; renderWorkspace(); toast('修改已保存');}
    if (button.dataset.action === 'discard') {state.dirty.delete(id); card.dataset.version = ''; renderWorkspace();}
  } catch(e) {fail(e);} finally {button.disabled = false;}
});
$('#canvas').addEventListener('change',async e => {
  const card = e.target.closest('.artifact-card'); if (!card) return;
  const a = state.workspace.artifacts.find(a => a.id === card.dataset.artifact);
  if (e.target.dataset.action === 'chart-column') updateChart(card,a.data,Number(e.target.value));
  if (e.target.dataset.action === 'task') {e.target.disabled = true; try {await mutateArtifact(a.id,{task_id:e.target.dataset.task,done:e.target.checked});} catch(error) {e.target.checked = !e.target.checked; fail(error);} finally {e.target.disabled = false;}}
});
window.addEventListener('popstate',() => {if (state.dirty.size) {history.pushState({},'','/w/'+state.workspace.id); toast('先保存或放弃文稿修改，再切换空间。');} else openWorkspace(routePath(),false).catch(fail);});
window.addEventListener('beforeunload',e => {if (state.dirty.size) {e.preventDefault(); e.returnValue = '';}});
async function boot() {
  try {state.registry = await (await fetch('/registry.json')).json(); await openWorkspace(routePath(),false); input.focus();}
  catch(e) {$('#runtime-status').textContent = '连接暂不可用'; toast('无法打开工作区：'+e.message);}
}
boot();
