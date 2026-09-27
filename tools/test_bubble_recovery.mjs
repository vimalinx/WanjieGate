import assert from 'node:assert/strict';
import test from 'node:test';
import * as states from '../static/js/bubbles/state.mjs';
import {createClient} from '../static/js/bubbles/client.mjs';
const {initialState,mergeRequest,reduce}=states;
const source={id:'a',kind:'source',title:'Note',version:0,resource:{artifact:'note',version:0,detail:'full'}};
const action={id:'b',kind:'action',title:'Write',resource:{action:'write'}};
let s=initialState({input:'写一篇草稿',bubbles:[source,action],runs:{old:{runId:'old',status:'success',sources:[{version:0}]}}});
let request=mergeRequest(s,'a','b'),session={id:'a',target:'b',request};
s=reduce(s,{type:'mergeStart',request});
test('release rejects timed-out, invalidated and edited drag sessions',()=>{
assert.equal(states.releaseDisposition(s,session),'wait');
assert.equal(states.releaseDisposition(reduce(s,{type:'mergeCancel'}),session),'restore','timeout before release restores canvas');
assert.equal(states.releaseDisposition(reduce(s,{type:'input',text:'不要写正文'}),session),'restore');
let changed=structuredClone(s);changed.bubbles[0].version++;
assert.equal(states.releaseDisposition(changed,session),'restore','source edits invalidate held drag');
});
test('source refresh invalidates pending judgment and preserves historical runs',()=>{
const refreshed=reduce(s,{type:'refreshSource',artifact:{id:'note',version:1,title:'Updated note'}});
assert.equal(refreshed.bubbles[0].resource.version,1);assert.equal(refreshed.pending,null);assert.deepEqual(refreshed.runs,s.runs);
});
test('manual fallback exposes supported operations and respects negation',()=>{
assert.deepEqual(states.manualMergeOptions(s,'a','b').map(x=>x.id),['combine']);
assert.equal(states.manualMergeOptions({...s,input:'不要代写正文'},'a','b').length,0);
let links=initialState({bubbles:[source,{id:'link',kind:'link',resource:{url:'https://example.com'}}]});
assert.equal(states.manualMergeOptions(links,'a','link').length,0);
const many=initialState({bubbles:Array.from({length:5},(_,i)=>({id:'s'+i,kind:'source',resource:{url:'https://example.com/'+i}})),groups:[{id:'g',operation:'collect',members:['s0','s1','s2','s3']}]});
assert.equal(states.manualMergeOptions(many,'g','s4').length,0,'manual path must enforce the four step limit');
});
test('interrupted runs can be explicitly run again',()=>{
const interrupted=initialState({runs:{g:{runId:'old',status:'interrupted'}}});
assert.equal(reduce(interrupted,{type:'runAgain',groupId:'g',runId:'new'}).runs.g.runId,'new');
});
test('lost-before-acceptance replay uses same identity and accepted run is not replayed',async()=>{
let posts=[],accepted=null,failBeforeAccept=true;
const storage={getItem(k){return this[k]??null},setItem(k,v){this[k]=v},removeItem(k){delete this[k]}};
const transport=async(path,body)=>{if(!body)return {found:!!accepted,response:accepted};posts.push(structuredClone(body));if(failBeforeAccept){failBeforeAccept=false;throw new Error('lost before acceptance')}accepted={task:{id:'task-1',status:'queued'}};return accepted};
const client=createClient(transport,storage);client.setIntent('intent');const payload={runId:'original-run',canvas:'canvas',version:2,groupId:'group',text:'write'};
await assert.rejects(client.run(payload));
const run={runId:payload.runId,payload,status:'outcome_unknown'};
assert.equal((await client.recover(run)).found,false);assert.equal(posts.length,1);
assert.equal((await client.recover(run,{resubmit:true})).response.task.id,'task-1');
assert.equal(posts.length,2);assert.equal(posts[0].id,posts[1].id);assert.deepEqual(posts[0].payload,posts[1].payload);
assert.equal((await client.recover(run,{resubmit:true})).found,true);assert.equal(posts.length,2,'accepted run is never posted twice');
});
test('independent combinations never share the same default display position',()=>{
 const canvas=initialState({bubbles:[],groups:[{id:'g1',operation:'collect',members:[]},{id:'g2',operation:'collect',members:[]}],positions:{g1:{x:.5,y:.78},g2:{x:.5,y:.78}}});
 const positions=states.layoutPositions(canvas,[[.22,.31],[.5,.27],[.78,.31]]);
 assert.deepEqual(positions.g1,{x:.5,y:.78});assert.notDeepEqual(positions.g1,positions.g2);
});
