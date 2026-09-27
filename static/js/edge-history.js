// Pointer proximity reveals history without making the writing surface inert.
export function installEdgeHistory(drawer, edge) {
 let opening, closing, hoverOpened=false;
 const clear=()=>{clearTimeout(opening);clearTimeout(closing);};
 const available=()=>!document.querySelector('#dialog[open]')
  && !document.body.matches('.dragging-block, .dragging-material')
  && ![...document.querySelectorAll('[data-lane="left"] .growth-block:not([hidden])')]
   .some(block=>block.getBoundingClientRect().width>0);
 const open=hover=>{
  clear();
  if(drawer.open)return;
  hoverOpened=hover;
  if(hover){
   const focused=document.activeElement;
   drawer.show();
   // HTML dialog focusing steps must not interrupt the document caret.
   focused?.focus({preventScroll:true});
   if(drawer.contains(document.activeElement))document.activeElement.blur();
  }else drawer.showModal();
  edge.setAttribute('aria-expanded','true');
 };
 const closeSoon=()=>{
  clearTimeout(opening);clearTimeout(closing);
  if(!hoverOpened)return;
  closing=setTimeout(()=>{
   if(!drawer.matches(':hover')&&!edge.matches(':hover')&&!drawer.contains(document.activeElement))drawer.close();
  },260);
 };
 edge.addEventListener('pointerenter',event=>{
  clear();
  if(event.pointerType!=='mouse'||event.buttons||!available())return;
  opening=setTimeout(()=>{if(edge.matches(':hover')&&available())open(true);},180);
 });
 edge.addEventListener('pointerleave',closeSoon);
 edge.addEventListener('click',()=>open(false));
 drawer.addEventListener('pointerenter',clear);
 drawer.addEventListener('pointerleave',closeSoon);
 drawer.addEventListener('focusout',closeSoon);
 drawer.addEventListener('close',()=>{clear();hoverOpened=false;edge.setAttribute('aria-expanded','false');});
 document.addEventListener('pointerdown',event=>{
  if(hoverOpened&&!drawer.contains(event.target)&&!edge.contains(event.target))drawer.close();
 });
 document.addEventListener('keydown',event=>{
  if(event.key==='Escape'&&hoverOpened){event.preventDefault();drawer.close();}
 });
 window.addEventListener('blur',()=>{clear();if(hoverOpened)drawer.close();});
 return {open:()=>open(false)};
}
