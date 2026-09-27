// A new workspace keeps the live input node; departing objects are visual copies.
export async function returnToOrigin({reset,slide=false}) {
 const reduced=document.body.classList.contains('motion-off')||matchMedia('(prefers-reduced-motion: reduce)').matches;
 const capsule=document.querySelector('.capsule'),from=capsule.getBoundingClientRect();
 const copies=[];
 if(!reduced){
  const nodes=[...document.querySelectorAll('.growth-block:not([hidden]),#content [data-projection],#writer-heading,#workspace>.work-heading'+(slide?',.capsule':''))];
  for(const [index,node] of nodes.entries()){
   const rect=node.getBoundingClientRect();
   if(!rect.width||!rect.height||rect.bottom<0||rect.top>innerHeight)continue;
   const copy=node.cloneNode(true);
   // Freeze the departing projection before body styles change back to the origin.
   const originals=[node,...node.querySelectorAll('*')],replicas=[copy,...copy.querySelectorAll('*')];
   const properties=['display','box-sizing','font','color','line-height','letter-spacing','background','border','border-radius','padding','box-shadow','gap','align-items','justify-content','flex-direction'];
   originals.forEach((original,i)=>{
    const computed=getComputedStyle(original),replica=replicas[i];
    for(const property of properties)replica.style.setProperty(property,computed.getPropertyValue(property));
    if(original instanceof HTMLTextAreaElement||original instanceof HTMLInputElement){
     replica.value=original.value;replica.style.height=original.getBoundingClientRect().height+'px';
    }
   });
   copy.removeAttribute('id');
   copy.querySelectorAll('[id]').forEach(el=>el.removeAttribute('id'));
   copy.inert=true;copy.setAttribute('aria-hidden','true');
   Object.assign(copy.style,{position:'fixed',left:rect.left+'px',top:rect.top+'px',width:rect.width+'px',height:rect.height+'px',margin:0,pointerEvents:'none',zIndex:5});
   document.body.append(copy);copies.push(copy);
   const animation=copy.animate([{opacity:1,transform:'translateX(0)'},{opacity:0,transform:`translateX(${slide?-innerWidth:-80}px)`}],{duration:slide?280:180,delay:Math.min(index*16,48),easing:'cubic-bezier(.4,0,1,1)',fill:'forwards'});
   animation.finished.catch(()=>{}).finally(()=>copy.remove());
  }
 }
 // Disable page padding interpolation so the live capsule can use FLIP geometry.
 document.body.classList.add('returning-origin');
 try{
  await reset();
  window.scrollTo({top:0,left:0,behavior:'instant'});
  const to=capsule.getBoundingClientRect();
  if(!reduced&&from.width&&to.width){
   capsule.getAnimations().forEach(animation=>animation.cancel());
   const shift=slide?-Math.min(100,innerWidth*.12):0;
   const animation=capsule.animate([
    {boxSizing:'border-box',width:from.width+'px',height:from.height+'px',transform:`translate(${from.left-to.left}px,${from.top-to.top}px)`,borderRadius:'4px',opacity:.7},
    {offset:.35,boxSizing:'border-box',width:to.width*1.03+'px',height:to.height*1.25+'px',transform:`translate(${shift}px,${(from.top-to.top)*.28}px)`,borderRadius:'26px',opacity:.9},
    {boxSizing:'border-box',width:to.width+'px',height:to.height+'px',transform:'translate(0,0)',borderRadius:'36px',opacity:1}
   ],{duration:340,easing:'cubic-bezier(.2,.75,.2,1)'});
   // Direct interaction immediately owns the input geometry.
   const interrupt=()=>animation.cancel();
   capsule.addEventListener('pointerdown',interrupt,{once:true});
   capsule.addEventListener('keydown',interrupt,{once:true});
   await animation.finished.catch(()=>{});
   capsule.removeEventListener('pointerdown',interrupt);capsule.removeEventListener('keydown',interrupt);
  }
 }finally{document.body.classList.remove('returning-origin');copies.forEach(copy=>copy.remove());}
}

export function installNextGesture(next) {
 let total=0,last=0,lockedUntil=0,touch=null;
 const blocked=()=>!!document.querySelector('dialog[open]')||document.body.matches('.dragging-block,.dragging-material');
 const scrollable=target=>{
  for(let el=target instanceof Element?target:null;el&&el!==document.body;el=el.parentElement){
   if(el.scrollWidth>el.clientWidth+4&&/auto|scroll/.test(getComputedStyle(el).overflowX))return true;
  }return false;
 };
 const trigger=()=>{lockedUntil=performance.now()+1000;total=0;Promise.resolve(next()).catch(()=>{});};
 window.addEventListener('wheel',event=>{
  if(event.ctrlKey||event.metaKey||blocked()||scrollable(event.target))return;
  const unit=event.deltaMode===1?16:event.deltaMode===2?innerWidth:1;
  const x=event.deltaX*unit,y=event.deltaY*unit;
  // Natural-scrolling trackpads report fingers moving right as negative deltaX.
  if(x>=0||Math.abs(x)<Math.abs(y)*1.6){total=0;return;}
  if(!event.cancelable)return;
  event.preventDefault();
  const now=performance.now();if(now<lockedUntil){lockedUntil=now+220;return;}
  if(now-last>220)total=0;last=now;total-=x;
  if(total>=110)trigger();
 },{passive:false});
 window.addEventListener('touchstart',event=>{
  if(event.touches.length!==2||blocked()||scrollable(event.target)){touch=null;return;}
  touch={distance:Math.hypot(event.touches[0].clientX-event.touches[1].clientX,event.touches[0].clientY-event.touches[1].clientY),x:(event.touches[0].clientX+event.touches[1].clientX)/2,y:(event.touches[0].clientY+event.touches[1].clientY)/2};
 },{passive:true});
 window.addEventListener('touchmove',event=>{
  if(!touch||event.touches.length!==2||blocked())return;
  const distance=Math.hypot(event.touches[0].clientX-event.touches[1].clientX,event.touches[0].clientY-event.touches[1].clientY);
  if(Math.abs(distance-touch.distance)>Math.max(18,touch.distance*.12)){touch=null;return;}
  const dx=(event.touches[0].clientX+event.touches[1].clientX)/2-touch.x;
  const dy=(event.touches[0].clientY+event.touches[1].clientY)/2-touch.y;
  if(dx>30&&dx>Math.abs(dy)*1.6&&event.cancelable)event.preventDefault();
  if(dx>110&&dx>Math.abs(dy)*1.6&&performance.now()>lockedUntil){touch=null;trigger();}
 },{passive:false});
 window.addEventListener('touchend',()=>{touch=null;},{passive:true});
 window.addEventListener('keydown',event=>{
  if((event.ctrlKey||event.metaKey)&&event.shiftKey&&event.key.toLowerCase()==='n'&&!blocked()){
   event.preventDefault();if(performance.now()>lockedUntil)trigger();
  }
 });
}
