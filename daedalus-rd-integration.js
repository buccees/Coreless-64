(function(){
'use strict';
var KEY='daedalus-rd-qualified-v1';
var sourceLabels={
 optics:{name:'OPTICAL TELESCOPE / PHOTONICS',target:'OPTICAL TELESCOPE'},
 specimen:{name:'REMOTE-PROBE SCIENCE PAYLOAD',target:'REMOTE PROBE / SCIENCE'},
 materials:{name:'SPACECRAFT STRUCTURES / MATERIALS',target:'STRUCTURES / POWER ENGINEERING'},
 'sensor-fusion':{name:'ORBITAL SENSOR FUSION',target:'RADAR / STAR TRACKER / INERTIAL NAVIGATION'}
};
function read(){try{var v=JSON.parse(localStorage.getItem(KEY)||'{}');return v&&typeof v==='object'?v:{};}catch(e){return {};}}
function write(v){try{localStorage.setItem(KEY,JSON.stringify(v));}catch(e){}}
var api=window.vigilDaedalusRDIntegration={
 schema:'vigil.daedalus-rd-integration',version:1,getQualifiedModules:read,
 qualify:function(source){
  var bus=window.CorelessRDLabBus,record=bus&&bus.latest(source);
  if(!record||!sourceLabels[source])return {ok:false,reason:'NO COMPLETED TEST RECORD FOR THIS WORKSPACE'};
  var state=read();state[source]={source:source,label:sourceLabels[source].name,target:sourceLabels[source].target,qualified_at:new Date().toISOString(),data:record.data,record_id:record.id};
  write(state);window.dispatchEvent(new CustomEvent('vigil:daedalus-rd-update',{detail:{source:source,record_id:record.id}}));render();
  return {ok:true,module:state[source]};
 }
};
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function render(){
 var host=document.getElementById('rd-active-labs');if(!host)return;
 var panel=host.querySelector('#daedalus-rd-qualification');if(!panel)return;
 var state=read(),rows=Object.keys(sourceLabels).map(function(key){
  var q=state[key],meta=sourceLabels[key];
  return '<div class="rd-lab-readout"><div><span>'+esc(meta.name)+'</span><b>'+(q?'QUALIFIED / '+esc(q.qualified_at):'NOT YET QUALIFIED')+'</b></div><div><span>COMPATIBLE DAEDALUS SYSTEM</span><b>'+esc(meta.target)+'</b></div></div>';
 }).join('');
 panel.querySelector('#daedalus-rd-qualified-list').innerHTML=rows;
 panel.querySelector('#daedalus-rd-status').textContent=Object.keys(state).length+' DAEDALUS MODULE(S) QUALIFIED // OTHER VEHICLE PROFILES UNAFFECTED';
}
function boot(){
 var host=document.getElementById('rd-active-labs');if(!host||host.querySelector('#daedalus-rd-qualification'))return;
 var panel=document.createElement('section');panel.id='daedalus-rd-qualification';panel.className='rd-lab-panel active';panel.style.marginTop='12px';
 panel.innerHTML='<div class="rd-lab-panel-head"><div><h4>DAEDALUS EQUIPMENT INTEGRATION / QUALIFICATION</h4><p>Test results enter the engineering archive first. Explicitly qualify a result to load its parameters into compatible Daedalus DE-01 equipment readouts. This interface cannot modify another vehicle.</p></div><span class="rd-lab-status">DE-01 ONLY</span></div><div class="rd-lab-controls"><label>ENGINEERING WORKSPACE<select id="daedalus-rd-source"><option value="optics">OPTICAL BENCH → OPTICAL TELESCOPE</option><option value="specimen">SPECIMEN ANALYSIS → REMOTE-PROBE SCIENCE</option><option value="materials">MATERIALS TEST → STRUCTURES / POWER</option><option value="sensor-fusion">ORBITAL SENSOR FUSION → RADAR / NAVIGATION</option></select></label><button type="button" id="daedalus-rd-qualify">QUALIFY LATEST TEST FOR DAEDALUS</button><p id="daedalus-rd-status" role="status" aria-live="polite">NO ENGINEERING MODULES QUALIFIED</p></div><div id="daedalus-rd-qualified-list"></div>';
 host.appendChild(panel);
 panel.querySelector('#daedalus-rd-qualify').addEventListener('click',function(){
  var source=panel.querySelector('#daedalus-rd-source').value,result=api.qualify(source);
  panel.querySelector('#daedalus-rd-status').textContent=result.ok?'QUALIFICATION ACCEPTED // '+result.module.label+' // DAEDALUS DE-01 ONLY':result.reason;
 });
 render();
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
window.addEventListener('coreless:rd-data',render);
window.addEventListener('vigil:daedalus-rd-update',render);
})();