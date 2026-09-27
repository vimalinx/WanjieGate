import {esc,markdown} from './components.js';
import {createCompositionPolicy} from './composition-policy.js';
import {motion,relocate,stopMotion,disposeMotion} from './semantic-motion.js';
import {catalogReady,descriptor,ExtensionHost,MATERIAL,encodeMaterial,decodeMaterial} from './component-registry.js';
import {sceneSurfaces} from './scene.js';

const terminal=new Set(['success','failure','partial','cancelled','interrupted','outcome_unknown']);
const $=s=>document.querySelector(s);
const titleOf=text=>text.split('\n').find(x=>x.trim())?.replace(/^#+\s*/,'').slice(0,60)||'未命名笔记';
const safeURL=url=>/^https:\/\/[^\s<>"']+$/.test(url||'')?url:'';

export class AdaptiveSpace {
 constructor(host){
  this.host=host;this.policy=createCompositionPolicy();this.parked=new Set();this.extensions=new ExtensionHost(this);catalogReady.then(()=>{if(this.owner){this.renderSupports();this.extensions.update();}}).catch(host.fail);this.owner=null;this.mode='general';this.blocks=new Map();this.payloads=new Map();this.pending=new Map();this.seen=new Set();this.layout={};this.saveChain=Promise.resolve();this.revision=0;this.viewRevision=0;this.lastSelection="";this.dirty=false;this.hydrated=false;this.note=null;this.manual=false;this.editor=$('#request');this.undo=[];
  $('#surface-switch').addEventListener('click',e=>{const b=e.target.closest('[data-surface]');if(b)this.switchMode(b.dataset.surface,true).catch(host.fail);});
  $('#document-title').oninput=()=>this.changed();
  $('#document-preview-toggle').onclick=()=>{const showing=!$('#document-preview').hidden;$('#document-preview').hidden=showing;this.editor.hidden=!showing;$('#document-preview-toggle').textContent=showing?'阅读':'编辑';this.preview();};
  $('#writer-format').onclick=e=>{const b=e.target.closest('[data-format]');if(!b)return;const selected=this.editor.value.slice(this.editor.selectionStart,this.editor.selectionEnd);this.insert({text:{heading:'\n## 小标题\n',bold:'**'+(selected||'重点')+'**',quote:'\n> '+(selected||'引用内容')+'\n',check:'\n- [ ] 待办事项\n',link:'['+(selected||'链接文字')+'](https://)' }[b.dataset.format]});};
  $('#document-export').onclick=()=>this.export();
  $('#writer-undo').onclick=()=>{const previous=this.undo.pop();if(previous){this.editor.value=previous.text;this.editor.setSelectionRange(previous.start,previous.end);this.input();}};
  $('#image-import').onchange=e=>this.importFiles(e.target.files).catch(host.fail);
  $('#surface-tools').onclick=e=>{const b=e.target.closest('[data-helper]');if(!b)return;this.force=this.force||{};this.force[b.dataset.helper]=true;const key=b.dataset.helper;this.policy.restore(this.owner+':'+key);this.parked.delete(key);if(this.layout[key]){this.layout[key].hidden=false;this.persist().catch(host.fail);}this.renderSupports();if(b.dataset.helper==='references')this.search($('#reference-query')?.value||this.topic()).catch(host.fail);if(b.dataset.helper==='images')$('#image-import').click();};
  $('#surface-history').onclick=()=>$('#history-open').click();
  for(const lane of document.querySelectorAll('[data-lane]')){
   lane.addEventListener('dragover',e=>{if([...e.dataTransfer.types].some(t=>['application/x-wanjie-block','application/x-wanjie-material',MATERIAL,'text/plain'].includes(t))){e.preventDefault();e.dataTransfer.dropEffect='move';lane.classList.add('drop-target');}});
   lane.addEventListener('dragleave',e=>{if(!lane.contains(e.relatedTarget))lane.classList.remove('drop-target');});
   lane.addEventListener('drop',e=>{lane.classList.remove('drop-target');const key=e.dataTransfer.getData('application/x-wanjie-block');if(!key){const material=decodeMaterial(e.dataTransfer.getData(MATERIAL),this.owner)||this.payloads.get(e.dataTransfer.getData('application/x-wanjie-material'));const text=material?.text||e.dataTransfer.getData('text/plain');if(text){e.preventDefault();this.splitNote(text,material?.artifact).catch(host.fail);}return;}e.preventDefault();const target=e.target.closest('[data-block]');this.move(key,lane.dataset.lane,target?.dataset.block);});
  }
  document.addEventListener('dragstart',e=>{
   const item=e.target.closest('[data-material]');const handle=e.target.closest('[data-handle]');
   if(item){const payload=this.payloads.get(item.dataset.material);if(!payload)return;e.dataTransfer.setData(MATERIAL,encodeMaterial(item.dataset.material,this.owner,payload));e.dataTransfer.setData('application/x-wanjie-material',item.dataset.material);e.dataTransfer.setData('text/plain',payload.text);e.dataTransfer.effectAllowed='copy';document.body.classList.add('dragging-material');}
   else if(handle){stopMotion(handle.closest('[data-block]'));e.dataTransfer.setData('application/x-wanjie-block',handle.dataset.handle);e.dataTransfer.effectAllowed='move';document.body.classList.add('dragging-block');}
  });
  document.addEventListener('dragend',()=>{document.body.classList.remove('dragging-material','dragging-block');document.querySelectorAll('.drop-target').forEach(e=>e.classList.remove('drop-target'));});
  this.editor.addEventListener('select',()=>{const signature=[this.editor.selectionStart,this.editor.selectionEnd].join(':');if(signature!==this.lastSelection){this.lastSelection=signature;this.viewRevision++;if(this.editor.selectionStart!==this.editor.selectionEnd)this.host.contextChanged?.();}if(this.owner&&this.mode==='writing')sessionStorage.setItem('growth-caret:'+this.owner,JSON.stringify({start:this.editor.selectionStart,end:this.editor.selectionEnd}));});
  this.editor.addEventListener('dragover',e=>{if([...e.dataTransfer.types].some(t=>['application/x-wanjie-material',MATERIAL,'Files','text/plain','text/uri-list'].includes(t))){e.preventDefault();e.dataTransfer.dropEffect='copy';this.editor.classList.add('drop-target');}});
  this.editor.addEventListener('dragleave',()=>this.editor.classList.remove('drop-target'));
  this.editor.addEventListener('drop',e=>{
   e.preventDefault();this.editor.classList.remove('drop-target');const index=this.dropOffset(e.clientX,e.clientY);this.editor.setSelectionRange(index,index);
   if(e.dataTransfer.files.length){this.importFiles(e.dataTransfer.files,true).catch(host.fail);return;}
   const key=e.dataTransfer.getData('application/x-wanjie-material');const p=decodeMaterial(e.dataTransfer.getData(MATERIAL),this.owner)||this.payloads.get(key);
   if(p)this.insert(p);else {const text=e.dataTransfer.getData('text/plain');if(text)this.insert({text:text.slice(0,12000)});}
  });
  $('#adaptive-grid').addEventListener('click',e=>this.click(e).catch(host.fail));
  this.editor.addEventListener('paste',e=>{const files=[...(e.clipboardData?.items||[])].filter(i=>i.kind==='file'&&i.type.startsWith('image/')).map(i=>i.getAsFile());if(files.length){e.preventDefault();this.importFiles(files,true).catch(host.fail);}});
 }
 state(){return this.host.state();}
 semanticContext(){return {revision:this.viewRevision,document:this.note||'',selection:this.editor.value.slice(this.editor.selectionStart,this.editor.selectionEnd).slice(0,1200),blocks:[...this.blocks.values()].slice(0,16).map(b=>({id:b.key,title:(b.el.querySelector('h2')?.textContent||'').slice(0,200),excerpt:(b.el.querySelector('.growth-body')?.textContent||'').slice(0,600),pinned:!!this.layout[b.key]?.pinned,hidden:b.el.hidden}))};}

 topic(){return this.presentation?.query||titleOf(this.editor.value).slice(0,60);}
 input(){this.editor.dispatchEvent(new Event('input',{bubbles:true}));}
 changed(){this.viewRevision++;if(this.mode!=='writing'){this.extensions.update();return;}this.dirty=true;this.revision++;this.cache();clearTimeout(this.saveTimer);this.saveTimer=setTimeout(()=>this.save().catch(this.host.fail),650);this.outline();this.resize();this.preview();this.extensions.update();$('#document-save').textContent='正在保存…';}
 cache(){if(this.owner&&this.mode==='writing')sessionStorage.setItem('growth-draft:'+this.owner,JSON.stringify({text:this.editor.value,title:$('#document-title').value,at:Date.now(),note:this.note}));}
 resize(){if(this.mode==='writing'){this.editor.style.height='auto';this.editor.style.height=Math.max(490,this.editor.scrollHeight)+'px';}}
 async save(){
  const owner=this.owner;if(!owner||this.mode!=='writing')return this.saveChain;
  const text=this.editor.value,title=$('#document-title').value||titleOf(text),revision=this.revision;
  this.saveChain=this.saveChain.catch(()=>{}).then(async()=>{
   if(this.owner!==owner)return;
   if(!this.note){const r=await this.host.command('artifact.create',{kind:'note',title,content:{text},source:'用户写作'},owner);if(this.owner!==owner)return;this.note=r.value.id;this.noteVersion=r.value.version;await this.persist();}
   else{const existing=this.state().artifacts?.find(a=>a.id===this.note);const r=await this.host.command('artifact.update',{artifact:this.note,version:this.noteVersion??existing?.version??0,title,content:{text}},owner);this.noteVersion=r.value.version;}
   if(this.owner===owner&&this.revision===revision){this.dirty=false;$('#document-save').textContent='已保存';sessionStorage.removeItem('growth-draft:'+owner);}
  }).catch(e=>{if(this.owner===owner){$('#document-save').textContent='未保存 · '+e.message;this.cache();}throw e;});return this.saveChain;
 }
 async persist(){this.viewRevision++;if(!this.owner)return;await this.host.command('surface.update',{mode:this.mode,document:this.note||'',manual:this.manual,blocks:this.layout},this.owner);}
 update(state,owner){
  if(owner!==this.owner){
   clearTimeout(this.saveTimer);this.extensions.clear();this.policy.clear();this.parked.clear();this.viewRevision++;this.owner=owner;this.mode=state.surface?.document||state.surface?.mode==='writing'?'writing':'general';this.note=state.surface?.document||null;this.manual=state.surface?.manual||false;this.layout=state.surface?.blocks||{};this.blocks.forEach(b=>{disposeMotion(b.el);b.el.remove();});this.blocks.clear();this.payloads.clear();this.pending.clear();this.seen.clear();this.presentation=null;this.referencesId=(state.artifacts||[]).filter(a=>a.kind==='references').at(-1)?.id;this.marketId=null;this.lastError=null;this.queryOverride='';this.force={references:false,market:(state.artifacts||[]).some(a=>a.kind==='scene'&&a.content.blocks?.some(b=>b.type==='quotes'))};if(this.referencesId)this.policy.restore(owner+':references');this.referenceSource='web';if(this.referencesId){const content=state.artifacts.find(a=>a.id===this.referencesId).content;this.seen.add('ref:'+content.query);this.referenceSource=content.source.startsWith('Wikipedia')?'wikipedia':'web';}this.undo=[];this.dirty=false;this.revision=0;this.saveChain=Promise.resolve();
   if(this.mode==='writing'){const a=state.artifacts?.find(a=>a.id===this.note);let local=null;try{local=JSON.parse(sessionStorage.getItem('growth-draft:'+owner));}catch{}
    if(a){this.editor.value=a.content.text||'';$('#document-title').value=a.title;this.noteVersion=a.version;}
    if(local&&(!a||local.at>a.updated)){this.editor.value=local.text;$('#document-title').value=local.title;this.dirty=true;this.revision++;}
   }
   this.renderShelf();this.applyMode();if(this.mode==='writing'){try{const pos=JSON.parse(sessionStorage.getItem('growth-caret:'+owner));if(pos)this.editor.setSelectionRange(pos.start,pos.end);}catch{}}if(this.dirty)this.saveTimer=setTimeout(()=>this.save().catch(this.host.fail),650);
  }
  if(!owner){this.applyMode();return;}
  const p=state.presentation;
  if(p&&p.task!==this.presentation?.task&&p.text===this.editor.value.trim()&&(p.viewRevision==null||p.viewRevision===this.viewRevision)){
   this.presentation=p;
   if(p.editor>=.75&&this.mode!=='writing')this.switchMode('writing',false).catch(this.host.fail);
   if(p.market>=.75)this.renderMarket();
  }
  this.renderSupports();
  if(this.force?.market||this.mode==='market'||this.blocks.has('market'))this.renderMarket();
  for(const [key,pending] of [...this.pending]){
   const task=state.tasks?.find(t=>t.id===pending.id);if(!task||!terminal.has(task.status))continue;
   this.pending.delete(key);if(pending.owner!==owner)continue;
   if(task.status!=='success'){this.lastError={key,text:task.error?.message||'暂时不可用'};this.renderSupports();this.renderMarket();continue;}
   if(key==='references')this.referencesId=task.artifacts[0];
   if(key==='market')this.marketId=task.artifacts[0];
   this.renderSupports();this.renderMarket();
  }
  this.extensions.update();this.resize();
 }
 applyMode(){
  document.body.dataset.surface=this.mode;$('#surface-bar').hidden=!this.owner;$('#writer-heading').hidden=this.mode!=='writing';$('#writer-format').hidden=this.mode!=='writing';$('#surface-tools').hidden=!this.owner;
  // These controls add objects, not exclusive modes.
  this.editor.setAttribute('aria-label',this.mode==='writing'?'笔记正文':'当前请求');this.editor.placeholder=this.mode==='writing'?'从这里开始写。材料可以直接拖进来。':this.mode==='market'?'输入股票名称或代码，例如 600519、AAPL…':'想做什么？';
  $('#document-preview').hidden=true;this.editor.hidden=false;$('#document-preview-toggle').textContent='阅读';
  // Components retain independent identity and visibility across editor expansion.
  this.resize();
 }
 async switchMode(mode,manual){
  if(!this.owner)await this.host.ensure();if(mode===this.mode){if(manual){this.manual=mode!=='general';await this.persist();}return;}
  if(mode==='market'){this.force={...this.force,market:true};this.layout.market={...this.layout.market,hidden:false};this.renderMarket();await this.persist();return;}
  const previous=this.mode;if(previous==='writing'){this.cache();await this.save();sessionStorage.setItem('growth-writing:'+this.owner,this.editor.value);}
  this.mode=mode;this.manual=manual&&mode!=='general';
  if(mode==='writing'){
   const a=this.state().artifacts?.find(a=>a.id===this.note);
   if(a&&previous!=='general'){this.editor.value=a.content.text;$('#document-title').value=a.title;}
   else if(!this.note)$('#document-title').value=titleOf(this.editor.value);
   this.dirty=true;this.changed();
  }else if(previous==='writing'){this.editor.value='';sessionStorage.setItem('runtime-draft:'+this.owner,'');}
  this.applyMode();if(manual)motion($('.growth-center'),'EXPAND',{human:true});await this.persist();if(mode==='writing')this.renderSupports();if(mode==='market')this.renderMarket();
 }
 block(key,title,html,lane='right',signature=html){
  const declared=descriptor(key);title=declared?.title||title;lane=declared?.placement||lane;const config=this.layout[key]||{};let block=this.blocks.get(key);
  if(config.hidden&&!config.pinned){if(block)block.el.hidden=true;return null;}
  if(!block){const el=document.createElement('section');el.className='growth-block';el.dataset.block=key;el.innerHTML=`<header class="growth-head"><button class="block-handle" draggable="true" data-handle="${esc(key)}" aria-label="拖动${esc(title)}">⠿</button><h2>${esc(title)}</h2><button data-block-pin="${esc(key)}" aria-label="固定${esc(title)}">◇</button><details class="block-menu"><summary aria-label="${esc(title)}选项">···</summary><div><button data-block-left="${esc(key)}">移到左侧</button><button data-block-right="${esc(key)}">移到右侧</button><button data-block-bottom="${esc(key)}">移到下方</button><button data-block-hide="${esc(key)}">收起</button></div></details></header><div class="growth-body"></div>`;block={key,el,signature:null};this.blocks.set(key,block);}
  block.el.hidden=false;block.el.classList.toggle('is-pinned',!!config.pinned);block.el.querySelector('[data-block-pin]').setAttribute('aria-pressed',String(!!config.pinned));
  if(block.signature!==signature&&!block.el.contains(document.activeElement)){block.el.querySelector('.growth-body').innerHTML=html;block.signature=signature;}
  const parent=document.querySelector(`[data-lane="${config.lane||lane}"]`);if(block.el.parentElement!==parent){if(block.el.isConnected)relocate(block.el,()=>parent.append(block.el));else{parent.append(block.el);motion(block.el,'APPROACH');}}
  block.el.style.order=String(config.order??this.blocks.size);return block;
 }
 renderSupports(){
  if(!this.owner)return;
  this.outline();const text=this.editor.value;const supports=this.presentation?.supports||{};
  const notes=(this.state().artifacts||[]).filter(a=>['note','document','memory'].includes(a.kind)&&a.intent===this.owner&&a.id!==this.note);
  if(this.mode==='writing')this.block('notes','这个空间的笔记','<button data-new-note>＋ 新笔记</button>'+(notes.length?notes.map(a=>{const key='note:'+a.id;this.payloads.set(key,{text:`\n[[${a.title}]]\n`,artifact:a.id});return `<div class="note-material" draggable="true" data-material="${key}"><button data-open-note="${a.id}">${esc(a.title)}</button><small>${esc((a.content.text||'').slice(0,75))}</small><button data-insert="${key}">链接到正文</button></div>`;}).join(''):'<p class="growth-empty">新的笔记会留在这个空间。</p>')+'<p class="growth-empty">拖入一段文字，保存为独立笔记。</p>','left');
  if(this.mode==='writing'&&(text.length>180||this.force?.outline))this.block('structure','写作进度',`<div class="writing-metrics"><strong>${text.replace(/\s/g,'').length}<small>字</small></strong><strong>${text.split(/\n\s*\n/).filter(x=>x.trim()).length}<small>段落</small></strong><strong>${Math.max(1,Math.ceil(text.length/450))}<small>分钟阅读</small></strong></div><button data-format="heading" class="structure-heading">＋ 添加小标题</button>`,'left');
  if(this.shouldShow('references',supports.references,!!this.force?.references)){
   const query=this.queryOverride||(this.topic()+(supports.cases>=.75&&this.referenceSource!=='wikipedia'?' 实践案例':''));this.block('references','资料与引用',`<form id="reference-search"><label class="sr-only" for="reference-query">参考资料关键词</label><input id="reference-query" value="${esc(query)}" placeholder="查找案例、概念或资料"><button type="submit">查找</button></form><select id="reference-source" aria-label="资料来源"><option value="web" ${this.referenceSource==='web'?'selected':''}>网页案例 · 搜索摘要</option><option value="wikipedia" ${this.referenceSource==='wikipedia'?'selected':''}>百科资料 · 原文摘录</option></select><div id="reference-results"></div>`);
   const selector=$('#reference-source');if(selector)selector.onchange=()=>{this.referenceSource=selector.value;this.search($('#reference-query').value).catch(this.host.fail);};const form=$('#reference-search');if(form)form.onsubmit=e=>{e.preventDefault();this.queryOverride=$('#reference-query').value;this.search(this.queryOverride).catch(this.host.fail);};
   this.referenceResults();if(query&&this.presentation?.text===this.editor.value.trim()&&!this.seen.has('ref:'+query)&&supports.references>=.7&&!this.layout.references?.hidden)this.search(query).catch(this.host.fail);
  }
  const images=(this.state().artifacts||[]).filter(a=>a.kind==='image');
  if(this.shouldShow('images',supports.images,!!images.length||!!this.force?.images)){
   const content=images.map(a=>{const key='image:'+a.id;this.payloads.set(key,{text:`\n![${a.title.replace(/[\[\]]/g,'') }](artifact://${a.id})\n`,artifact:a.id});const src=this.imageURL(a);return `<figure class="image-material" draggable="true" data-material="${key}">${src?`<img src="${esc(src)}" alt="${esc(a.title)}" loading="lazy">`:''}<figcaption>${esc(a.title)}<button data-insert="${key}">插入</button></figcaption></figure>`;}).join('');
   this.block('images','图片与截图',content+'<button data-import-images>＋ 导入图片或粘贴截图</button><p class="growth-empty">仅使用你导入的素材；拖入正文即可插图。</p>');
  }
  this.preview();
 }
 outline(){if(this.mode!=='writing')return;let offset=0;const headings=[];for(const line of this.editor.value.split('\n')){if(/^#{1,4}\s/.test(line))headings.push({text:line.replace(/^#+\s*/,''),offset});offset+=line.length+1;}
  this.block('outline','文档大纲',headings.length?headings.map(h=>`<button data-outline="${h.offset}">${esc(h.text)}</button>`).join(''):'<p class="growth-empty">用 # 写标题，结构会在这里展开。</p>','left');}
 async search(query){query=query.trim().slice(0,160);if(!query||this.pending.has('references'))return;this.seen.add('ref:'+query);this.lastError=null;this.referencesId=null;const owner=this.owner;this.pending.set('references',{id:'pending',owner});this.referenceResults();try{const task=await this.host.run('reference.search',{query,source:this.referenceSource||'web'},{automatic:true});if(owner===this.owner&&task)this.pending.set('references',{id:task.id,owner});}catch(e){if(owner===this.owner){this.pending.delete('references');this.lastError={key:'references',text:e.message};this.referenceResults();}}}
 referenceResults(){const target=$('#reference-results');if(!target)return;const data=this.state().artifacts?.find(a=>a.id===this.referencesId)?.content;const signature=JSON.stringify([this.referencesId,this.pending.get('references')?.id,this.lastError?.key==='references'?this.lastError.text:null,data?.entries?.length]);if(target.dataset.signature===signature)return;target.dataset.signature=signature;
  if(this.pending.has('references')){target.innerHTML='<p class="growth-loading">正在查找有来源的材料…</p>';return;}
  if(this.lastError?.key==='references'){target.innerHTML=`<p class="growth-error">${esc(this.lastError.text)}</p><button data-retry-references>重试</button>`;return;}
  if(!data){target.innerHTML='<p class="growth-empty">输入关键词，或等内容逐渐明确。</p>';return;}
  target.innerHTML=data.entries.length?data.entries.map(entry=>{const key='ref:'+this.referencesId+':'+entry.id;this.payloads.set(key,{text:`\n> ${entry.kind==='search-snippet'?'搜索摘要：':''}${entry.text.replace(/\n/g,'\n> ')}\n> — [${entry.title}](${entry.url})\n`,artifact:this.referencesId});return `<article class="reference-material" draggable="true" data-material="${key}"><span class="material-kicker">${entry.kind==='search-snippet'?'搜索摘要 · 打开来源核对':'原文摘录'}</span><h3>${esc(entry.title)}</h3><p>${esc(entry.text)}</p><footer><a href="${esc(safeURL(entry.url))}" target="_blank" rel="noopener noreferrer">来源 ↗</a><button data-insert="${key}">插入引用</button></footer>${entry.image?`<button data-reference-image="${entry.id}">查看配图</button>`:''}</article>`;}).join(''):'<p class="growth-empty">没有匹配的资料，试着换一个更具体的关键词。</p>';
 }
 renderMarket(){if(!this.owner||!this.shouldShow('market',this.presentation?.market,!!this.force?.market))return;const text=this.editor.value.trim();const p=this.presentation;
  if(p?.market>=.75&&text===p.text&&!this.seen.has('market:'+text))this.market(text).catch(this.host.fail);
  const a=this.state().artifacts?.find(a=>a.id===this.marketId)||(this.state().artifacts||[]).filter(a=>a.kind==='scene'&&a.content.blocks?.some(b=>b.type==='quotes')).at(-1);
  let html;if(this.pending.has('market'))html='<p class="growth-loading">正在连接行情来源…</p>';else if(this.lastError?.key==='market')html=`<p class="growth-error">${esc(this.lastError.text)}</p><button data-refresh-market>重新查询</button>`;else if(a)html='<div class="market-surfaces">'+sceneSurfaces(a.content).map(s=>{const q=(a.content.blocks||[]).flatMap(b=>b.type==='quotes'?b.items:[]).find(q=>s.key==='quote:'+q.symbol);const key=q?'quote:'+a.id+':'+q.symbol:'';if(q)this.payloads.set(key,{text:`\n### ${q.name} · ${q.symbol}\n\n报价 ${q.price} ${q.currency}，涨跌 ${q.percent}%。截至 ${q.asof}。\n[${q.source}](${q.url})\n`,artifact:a.id});return `<article class="market-tile" ${key?`draggable="true" data-material="${key}"`:''}>${s.html}${key?`<button data-quote-note="${key}">记入笔记 ↗</button>`:''}</article>`;}).join('')+'</div><button data-refresh-market>刷新行情</button>';else html='<p class="growth-empty">输入股票名称或代码，行情会在这里展开。</p><button data-refresh-market>查询当前输入</button>';
  this.block('market','市场观察',html,'bottom');
 }
 async market(text=this.editor.value.trim()){if(!text||this.pending.has('market'))return;this.seen.add('market:'+text);this.lastError=null;const owner=this.owner;this.pending.set('market',{id:'pending',owner});this.renderMarket();try{const t=await this.host.run('market.query',{text},{automatic:true});if(this.owner===owner&&t)this.pending.set('market',{id:t.id,owner});}catch(e){if(this.owner===owner){this.pending.delete('market');this.lastError={key:'market',text:e.message};this.renderMarket();}}}
 move(key,lane,before){
  const block=this.blocks.get(key);if(!block)return;
  const target=this.blocks.get(before),parent=document.querySelector(`[data-lane="${lane}"]`);
  const movement=relocate(block.el,()=>{
   parent.insertBefore(block.el,target?.el.parentElement===parent?target.el:null);
   [...parent.children].filter(el=>el.dataset.block).forEach((el,i)=>{this.layout[el.dataset.block]={...this.layout[el.dataset.block],lane,order:i,pinned:true};el.style.order=String(i);});
  },'EXPAND',true);
  this.persist().catch(this.host.fail);block.el.classList.add('is-pinned');
  movement.finished.then(result=>{if(result.status==='completed')motion(block.el,'FREEZE',{human:true});});
 }
 async click(e){const b=e.target.closest('button');if(!b)return;
  if(b.dataset.quoteNote){const payload=this.payloads.get(b.dataset.quoteNote);await this.switchMode('writing',true);this.insert(payload);}
  if(b.dataset.insert)this.insert(this.payloads.get(b.dataset.insert));
  if(b.dataset.outline!==undefined){this.editor.focus();this.editor.setSelectionRange(+b.dataset.outline,+b.dataset.outline);}
  if(b.dataset.blockPin){const key=b.dataset.blockPin;this.layout[key]={...this.layout[key],pinned:!this.layout[key]?.pinned};await this.persist();this.renderSupports();motion(this.blocks.get(key)?.el,'FREEZE',{human:true});}
  if(b.dataset.blockHide){const key=b.dataset.blockHide;this.layout[key]={...this.layout[key],hidden:true,pinned:false};const el=this.blocks.get(key).el;this.renderShelf();const destination=$('#component-shelf').querySelector(`[data-restore-block="${CSS.escape(key)}"]`);motion(el,'RECEDE',{to:destination?.getBoundingClientRect(),human:true,done:()=>{el.hidden=true;}});await this.persist();}
  for(const lane of ['left','right','bottom'])if(b.dataset['block'+lane[0].toUpperCase()+lane.slice(1)])this.move(b.dataset['block'+lane[0].toUpperCase()+lane.slice(1)],lane);
  if(b.hasAttribute('data-import-images'))$('#image-import').click();
  if(b.hasAttribute('data-retry-references'))await this.search($('#reference-query').value);
  if(b.hasAttribute('data-refresh-market'))await this.market();
  if(b.classList.contains('structure-heading'))this.insert({text:'\n## 小标题\n'});
  if(b.hasAttribute('data-new-note')){await this.save();this.note=null;this.noteVersion=0;this.editor.value='';$('#document-title').value='';this.revision++;this.dirty=true;await this.save();await this.host.refresh();this.editor.focus();}
  if(b.dataset.openNote){await this.save();const a=this.state().artifacts.find(a=>a.id===b.dataset.openNote);this.note=a.id;this.noteVersion=a.version;this.editor.value=a.content.text;$('#document-title').value=a.title;this.revision++;await this.persist();this.renderSupports();this.resize();}
  if(b.dataset.referenceImage){const entry=this.state().artifacts.find(a=>a.id===this.referencesId)?.content.entries.find(x=>x.id===b.dataset.referenceImage);if(entry&&safeURL(entry.image)){await this.host.command('artifact.create',{kind:'image',title:entry.title+' · 参考配图',content:{url:entry.image,description:entry.title,sourceURL:entry.url},source:entry.url});this.force.images=true;await this.host.refresh();}}
 }
 shouldShow(key,score,explicit=false){
  const block=this.blocks.get(key),config=this.layout[key]||{};
  const result=this.policy.evaluate(this.owner+':'+key,{score,sample:this.presentation?.task,pinned:config.pinned,explicit,interacting:!!block?.el.contains(document.activeElement)||document.body.classList.contains('dragging-block')||document.body.classList.contains('dragging-material'),dismissed:config.hidden});
  if(result.state==='park'){
   if(block&&!this.parked.has(key)&&!config.hidden){
    this.parked.add(key);this.renderShelf();const destination=$('#component-shelf').querySelector(`[data-restore-block="${CSS.escape(key)}"]`);
    motion(block.el,'RECEDE',{to:destination?.getBoundingClientRect(),done:()=>{block.el.hidden=true;}});
   }
   return false;
  }
  if(['hot','near'].includes(result.state)){
   if(this.parked.delete(key)){if(block){block.el.hidden=false;motion(block.el,'RETURN');}this.renderShelf();}
   return true;
  }
  return false;
 }
 renderShelf(){
  let shelf=$('#component-shelf');if(!shelf){shelf=document.createElement('nav');shelf.id='component-shelf';shelf.setAttribute('aria-label','收起的内容');$('#surface-bar').after(shelf);}shelf.replaceChildren();
  const keys=new Set([...Object.keys(this.layout).filter(k=>this.layout[k].hidden),...this.parked]);
  for(const key of keys){
   const button=document.createElement('button');button.dataset.restoreBlock=key;button.textContent=this.blocks.get(key)?.el.querySelector('h2')?.textContent||descriptor(key)?.title||key;
   button.onclick=()=>{
    this.layout[key]={...this.layout[key],hidden:false,pinned:true};this.policy.restore(this.owner+':'+key);this.parked.delete(key);
    const el=this.blocks.get(key)?.el;if(el){el.hidden=false;motion(el,'RETURN',{human:true});}
    this.renderSupports();this.renderMarket();this.extensions.update();this.persist().catch(this.host.fail);this.renderShelf();
   };shelf.append(button);
  }
 }
 insert(payload){if(!payload)return;if(this.mode!=='writing'){this.switchMode('writing',true).then(()=>this.insert(payload)).catch(this.host.fail);return;}const text=this.editor.value;this.undo.push({text,start:this.editor.selectionStart,end:this.editor.selectionEnd});this.undo=this.undo.slice(-20);this.editor.hidden=false;$('#document-preview').hidden=true;this.editor.focus({preventScroll:true});const start=this.editor.selectionStart,end=this.editor.selectionEnd;if(text.length-(end-start)+payload.text.length>12000){this.host.fail(new Error('本篇笔记已达到 12000 字符上限，请分成多篇'));return;}this.editor.setRangeText(payload.text,start,end,'end');this.input();if(payload.artifact&&this.note)this.host.command('relation.add',{subject:this.note,predicate:'references',object:payload.artifact}).catch(this.host.fail);}
 dropOffset(x,y){const r=this.editor.getBoundingClientRect(),style=getComputedStyle(this.editor),mirror=document.createElement('div');for(const prop of ['font','fontSize','fontFamily','lineHeight','letterSpacing','padding','border','boxSizing','wordBreak','tabSize'])mirror.style[prop]=style[prop];Object.assign(mirror.style,{position:'fixed',left:r.left+'px',top:r.top-this.editor.scrollTop+'px',width:r.width+'px',minHeight:r.height+'px',whiteSpace:'pre-wrap',overflowWrap:'break-word',zIndex:2147483647,opacity:'0'});mirror.textContent=this.editor.value||' ';document.body.append(mirror);const caret=document.caretPositionFromPoint?.(x,y);const range=!caret&&document.caretRangeFromPoint?.(x,y);const node=caret?.offsetNode||range?.startContainer,offset=caret?.offset??range?.startOffset;const result=node&&mirror.contains(node)?Math.min(this.editor.value.length,offset):this.editor.selectionStart;mirror.remove();return result;}
 async splitNote(text,source){if(!this.owner)return;const r=await this.host.command('artifact.create',{kind:'note',title:titleOf(text),content:{text:text.slice(0,12000)},source:'用户拖入侧栏'});const parent=source||this.note;if(parent)await this.host.command('relation.add',{subject:r.value.id,predicate:'derived_from',object:parent});await this.host.refresh();}
 imageURL(a){const c=a.content||{};return /^data:image\/(png|jpeg|webp);base64,[A-Za-z0-9+/=]+$/.test(c.data||'')?c.data:safeURL(c.url);}
 async importFiles(files,insert=false){if(!this.owner)await this.host.ensure();if(this.mode!=='writing')await this.switchMode('writing',true);for(const file of [...files].slice(0,6)){
   if(!['image/png','image/jpeg','image/webp'].includes(file.type)||file.size>15000000)throw new Error('支持 15 MB 以内的 PNG、JPEG 或 WebP 图片');
   const bitmap=await createImageBitmap(file),canvas=document.createElement('canvas');const scale=Math.min(1,1000/Math.max(bitmap.width,bitmap.height));canvas.width=Math.max(1,Math.round(bitmap.width*scale));canvas.height=Math.max(1,Math.round(bitmap.height*scale));canvas.getContext('2d').drawImage(bitmap,0,0,canvas.width,canvas.height);bitmap.close();let data=canvas.toDataURL('image/jpeg',.78);if(data.length>160000)data=canvas.toDataURL('image/jpeg',.35);if(data.length>190000)throw new Error('图片过大，请使用较小的截图');
   const r=await this.host.command('artifact.create',{kind:'image',title:file.name.slice(0,100),content:{data,description:file.name},source:'用户本地导入'});if(insert)this.insert({text:`\n![${file.name.replace(/[\[\]]/g,'')}](artifact://${r.value.id})\n`,artifact:r.value.id});
  }await this.host.refresh();}
 preview(){if($('#document-preview').hidden)return;let output=markdown(this.editor.value);output=output.replace(/!\[([^\]]*)\]\(artifact:\/\/([a-f0-9]+)\)/g,(_,caption,id)=>{const a=this.state().artifacts?.find(a=>a.id===id),url=a&&this.imageURL(a);return url?`<figure><img src="${esc(url)}" alt="${caption}"><figcaption>${caption}</figcaption></figure>`:caption;}).replace(/\[([^\]]+)\]\((https:\/\/[^\s<)]+)\)/g,(_,label,url)=>`<a href="${url}" target="_blank" rel="noopener noreferrer">${label} ↗</a>`).replace(/&gt; ([^<]+)/g,'<span class="preview-quote">$1</span>');$('#document-preview').innerHTML=output;}
 export(){const blob=new Blob([this.editor.value],{type:'text/markdown;charset=utf-8'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=($('#document-title').value||'笔记')+'.md';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}
}
