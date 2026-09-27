// Authored demonstration material. Prices, prose and the excerpt are fictional fixtures.
export const prose = '今天的风很热烈，我喜欢。\n\n从街角走回来，梧桐叶的影子铺满了人行道。我想把这些很小的瞬间记下来，等过些日子，再看看今天的自己。';
export const expandedProse = prose + '\n\n写作也许不需要先有一个完整的主题。先留下感受，再从一个具体场景开始：风吹过窗帘，杯子里的水微微晃动，远处有人推着自行车经过。';
export const reference = {
 query:'从日常场景开始写作', source:'演示材料 · 人工编写',
 entries:[{id:'demo-scene',kind:'demo',title:'让感受落在一个具体场景里',text:'演示示例：不急着解释“我很喜欢今天”，先写一件眼前发生的小事。让读者看到窗帘、树影与路过的人。',url:'',label:'模拟材料'}]
};
export const market = {
 status:'ready',title:'市场观察 · 模拟数据',blocks:[{type:'quotes',items:[
  {symbol:'DEMO-A',name:'青屿科技 · 演示',price:128.6,currency:'CNY',change:2.4,percent:1.90,asof:'2026-09-27T07:00:00Z',source:'模拟数据 · 非实时行情',url:'',period:'演示走势',points:[120,121.5,120.8,123,124,122.4,125.8,126.3,125.5,128.6].map(value=>({value}))},
  {symbol:'DEMO-B',name:'山川制造 · 演示',price:46.2,currency:'CNY',change:-.8,percent:-1.70,asof:'2026-09-27T07:00:00Z',source:'模拟数据 · 非实时行情',url:'',period:'演示走势',points:[47,46.7,47.3,47.1,46.4,46.8,46.1,46.4,46,46.2].map(value=>({value}))}
 ]}]
};

// Generated locally, with no image service or remote resource request.
export function illustration() {
 const canvas=document.createElement('canvas');canvas.width=600;canvas.height=380;
 const c=canvas.getContext('2d');c.fillStyle='#ececde';c.fillRect(0,0,600,380);
 c.fillStyle='#f8f6ed';c.fillRect(80,34,430,310);c.fillStyle='#c9d5c0';c.fillRect(104,54,384,246);
 c.fillStyle='#dfe5ca';c.beginPath();c.arc(386,130,72,0,Math.PI*2);c.fill();
 c.strokeStyle='#f8f6ed';c.lineWidth=10;c.beginPath();c.moveTo(295,54);c.lineTo(295,301);c.moveTo(104,183);c.lineTo(488,183);c.stroke();
 c.fillStyle='#e4e0d1';c.beginPath();c.moveTo(97,42);c.bezierCurveTo(183,136,42,218,169,314);c.lineTo(84,315);c.lineTo(84,42);c.fill();
 c.fillStyle='#72866c';c.fillRect(387,250,7,76);for(const [x,y,r] of [[374,254,15],[407,268,17],[377,285,13]]){c.beginPath();c.ellipse(x,y,r,8,-.6,0,Math.PI*2);c.fill();}
 c.fillStyle='#b7a994';c.fillRect(362,316,57,33);c.fillStyle='#6c7768';c.font='15px sans-serif';c.fillText('午后窗边 · 演示插图',24,366);
 return canvas.toDataURL('image/png');
}
