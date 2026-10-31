(function(){
'use strict';
var CARRIED=['DDG-51','SSN-774','DRONE-01','UUV-01','MECH-01'];
var LABELS={
 'DDG-51':'DDG-51 // ARLEIGH BURKE-CLASS DESTROYER',
 'SSN-774':'SSN-774 // VIRGINIA-CLASS SUBMARINE',
 'DRONE-01':'DRONE-01 // RECONNAISSANCE DRONE',
 'UUV-01':'UUV-01 // UNCREWED UNDERSEA VEHICLE',
 'MECH-01':'MECH-01 // GROUND / EVA MECH'
};
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function activeUnit(){return window.vigilGetActiveSimulationUnit&&window.vigilGetActiveSimulationUnit();}
function command(){return window.vigilMothershipCommand||null;}
function styles(){
 if(document.getElementById('vigil-mothership-command-style'))return;
 var st=document.createElement('style');st.id='vigil-mothership-command-style';
 st.textContent=`
 #vigil-mothership-command-terminal{border:1px solid #b18c45;background:linear-gradient(145deg,#171407,#070805);padding:11px;margin:10px 0 12px;color:#e9ddb4;font:10px/1.5 "Courier New",monospace;box-shadow:inset 0 0 0 1px #b18c4520,0 0 22px #9a74221a}
 #vigil-mothership-command-terminal[hidden]{display:none!important}
 #vigil-mothership-command-terminal .vmct-head{display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;border-bottom:1px solid #78602c;padding-bottom:8px;margin-bottom:8px}
 #vigil-mothership-command-terminal .vmct-head b{font-size:12px;letter-spacing:1.2px;color:#f4d48a}
 #vigil-mothership-command-terminal .vmct-head small{color:#ad9866;font-size:8px}
 #vigil-mothership-command-terminal .vmct-authority{border:1px solid #6b572a;background:#0b0b06;padding:7px;color:#ddc78b;margin-bottom:9px}
 #vigil-mothership-command-terminal .vmct-controls{display:grid;grid-template-columns:1.4fr 1fr 1fr;gap:7px;margin:8px 0}
 #vigil-mothership-command-terminal label{display:grid;gap:3px;color:#c4ad70;font-size:8px;letter-spacing:.6px}
 #vigil-mothership-command-terminal input,#vigil-mothership-command-terminal select{width:100%;min-width:0;padding:7px;background:#020805;color:#f1dfae;border:1px solid #66542d;font:10px "Courier New",monospace}
 #vigil-mothership-command-terminal .vmct-buttons{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0}
 #vigil-mothership-command-terminal button{background:#30240d;color:#ffe5a5;border:1px solid #a7833d;padding:8px 10px;font:9px "Courier New",monospace;cursor:pointer}
 #vigil-mothership-command-terminal button:disabled{opacity:.38;cursor:not-allowed}
 #vigil-mothership-command-terminal .vmct-launch{background:#17432d;border-color:#5eab72;color:#caffd7}
 #vigil-mothership-command-terminal .vmct-roster{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px;margin-top:9px}
 #vigil-mothership-command-terminal .vmct-craft{border:1px solid #564724;background:#080a06;padding:7px;min-width:0}
 #vigil-mothership-command-terminal .vmct-craft b{display:block;color:#e9d49a;font-size:9px;line-height:1.4;overflow-wrap:anywhere}
 #vigil-mothership-command-terminal .vmct-state{display:block;color:#86d39b;font-size:8px;margin:4px 0}
 #vigil-mothership-command-terminal .vmct-state.deployed{color:#ffd27c}
 #vigil-mothership-command-terminal .vmct-actions{display:flex;gap:4px;flex-wrap:wrap}
 #vigil-mothership-command-terminal .vmct-actions button{padding:5px 6px;font-size:8px}
 #vigil-mothership-command-terminal .vmct-status{border:1px solid #574925;background:#020603;padding:8px;min-height:36px;color:#f0dca7;white-space:pre-wrap;margin-top:8px}
 #vigil-mothership-command-terminal .vmct-note{font-size:8px;line-height:1.5;color:#aa9867;margin:8px 0 0}
 @media(max-width:620px){#vigil-mothership-command-terminal .vmct-controls{grid-template-columns:1fr 1fr}#vigil-mothership-command-terminal .vmct-controls label:first-child{grid-column:1/-1}#vigil-mothership-command-terminal .vmct-roster{grid-template-columns:1fr}}
 `;
 document.head.appendChild(st);
}
var root=null,lastStatus='MOTHERSHIP COMMAND // STANDBY';
function getManifest(){var api=command();return api&&api.getManifest?api.getManifest():[];}
function status(message){lastStatus=String(message||'');var el=root&&root.querySelector('#vmct-status');if(el)el.textContent=lastStatus;}
function getSelected(){return root&&root.querySelector('#vmct-craft-select').value||CARRIED[0];}
function currentVehicle(id){return getManifest().find(function(v){return v.id===id;})||null;}
function refreshRoster(){
 if(!root)return;
 var manifest=getManifest(),docked=manifest.filter(function(v){return v.deployment_status==='docked';}).length;
 root.querySelector('#vmct-bay-status').textContent='INTERNAL VEHICLE BAY // '+manifest.length+' ASSIGNED // '+docked+' SECURED // '+(manifest.length-docked)+' DEPLOYED';
 root.querySelector('#vmct-roster').innerHTML=manifest.map(function(v){
  var deployed=v.deployment_status==='deployed',state=deployed?'DEPLOYED / '+Number(v.speed||0).toFixed(4)+' MAP UNITS/S':'SECURED IN INTERNAL BAY';
  var d=deployed?'deployed':'';
  return '<article class="vmct-craft"><b>'+esc(LABELS[v.id]||v.name)+'</b><span class="vmct-state '+d+'">'+esc(v.bay_slot||'VEHICLE BAY')+' // '+esc(state)+'</span><div class="vmct-actions">'+
   (deployed?'<button type="button" data-action="hold" data-unit="'+esc(v.id)+'">HOLD</button><button type="button" data-action="recover" data-unit="'+esc(v.id)+'">RECOVER</button>':'<button type="button" class="vmct-launch" data-action="launch" data-unit="'+esc(v.id)+'">LAUNCH FROM DAEDALUS</button>')+
   '<button type="button" data-action="select" data-unit="'+esc(v.id)+'">SELECT</button></div></article>';
 }).join('');
 root.querySelectorAll('[data-action]').forEach(function(btn){btn.addEventListener('click',function(){var action=btn.dataset.action,id=btn.dataset.unit;execute(action,id);});});
 var chosen=currentVehicle(getSelected());
 root.querySelector('#vmct-launch-selected').disabled=!chosen||chosen.deployment_status!=='docked';
 root.querySelector('#vmct-hold-selected').disabled=!chosen||chosen.deployment_status!=='deployed';
 root.querySelector('#vmct-recover-selected').disabled=!chosen||chosen.deployment_status!=='deployed';
 root.querySelector('#vmct-launch-all').disabled=!docked;
}
function execute(action,id){
 var api=command();if(!api){status('COMMAND REJECTED // DAEDALUS COMMAND AUTHORITY OFFLINE');return;}
 var result;
 if(action==='launch'){
  var unit=currentVehicle(id),heading=root?(getSelected()===id?Number(root.querySelector('#vmct-heading').value):Number(unit&&unit.heading)):undefined,factor=root?Number(root.querySelector('#vmct-throttle').value):.25;
  var speed=unit?Math.max(.001,(Number(unit.max_speed)||0)*Math.max(.02,Math.min(1,factor))):undefined;
  result=api.launch(id,heading,speed);
 }else if(action==='hold')result=api.hold(id);
 else if(action==='recover')result=api.recover(id);
 else if(action==='select'){
  var sel=root.querySelector('#vmct-craft-select');sel.value=id;var unit=currentVehicle(id);if(unit)root.querySelector('#vmct-heading').value=String(Math.round(Number(unit.heading)||0));
  status('CRAFT SELECTED // '+id+' // COMMAND ROUTING: DAEDALUS-01');
 }else return;
 if(action!=='select'){
  status(result&&result.ok?'DAEDALUS COMMAND ACCEPTED // '+action.toUpperCase()+' // '+id:'DAEDALUS COMMAND DENIED // '+(result&&result.reason||'NO RESPONSE'));
 }
 refreshRoster();
}
function create(){
 var context=document.getElementById('vigil-unit-sensor-profile');if(!context||document.getElementById('vigil-mothership-command-terminal'))return;
 styles();root=document.createElement('section');root.id='vigil-mothership-command-terminal';
 root.innerHTML='<div class="vmct-head"><div><b>DAEDALUS // CARRIER COMMAND TERMINAL</b><br><small>FLIGHT OPERATIONS // BAY CONTROL // DEPLOYMENT AUTHORITY: DE-01</small></div><small id="vmct-bay-status">INTERNAL VEHICLE BAY // INITIALIZING</small></div>'+
 '<div class="vmct-authority">COMMAND PATH: VEHICLE BAY → DAEDALUS COMMAND COMPUTER → LAUNCH CONTROL → ASSIGNED VEHICLE HELM. Individual craft helms remain locked while secured aboard the mothership.</div>'+
 '<div class="vmct-controls"><label>SELECT STORED VEHICLE<select id="vmct-craft-select">'+CARRIED.map(function(id){return '<option value="'+id+'">'+esc(LABELS[id])+'</option>';}).join('')+'</select></label>'+
 '<label>LAUNCH HEADING / DEG<input id="vmct-heading" type="number" min="0" max="359" step="1" value="0"></label>'+
 '<label>LAUNCH THROTTLE / MAX SPEED<input id="vmct-throttle" type="number" min=".02" max="1" step=".02" value=".25"></label></div>'+
 '<div class="vmct-buttons"><button type="button" class="vmct-launch" id="vmct-launch-selected">ISSUE LAUNCH // DAEDALUS COMMAND</button><button type="button" id="vmct-hold-selected">HOLD SELECTED VEHICLE</button><button type="button" id="vmct-recover-selected">RECOVER TO MOTHERSHIP</button><button type="button" id="vmct-launch-all">LAUNCH ALL SECURED CRAFT</button></div>'+
 '<div class="vmct-subhead">DAEDALUS INTERNAL BAY MANIFEST // CARRIED VEHICLES</div><div id="vmct-roster" class="vmct-roster"></div><div id="vmct-status" class="vmct-status" role="status" aria-live="polite">MOTHERSHIP COMMAND // STANDBY</div>'+
 '<p class="vmct-note">The destroyer, submarine, drone, UUV and mech are assigned to Daedalus and start secured in its internal vehicle bays. Launch orders originate here. Recovery is accepted only inside the mothership capture envelope. FAC-01 is a fixed installation and is not stored aboard. All movement and telemetry are simulated.</p>';
 var deck=context.querySelector('#vigil-daedalus-deck-entry'),nav=context.querySelector('#vigil-navigation-controls');
 context.insertBefore(root,deck||nav||null);
 root.querySelector('#vmct-craft-select').addEventListener('change',function(){var chosen=currentVehicle(getSelected());if(chosen)root.querySelector('#vmct-heading').value=String(Math.round(Number(chosen.heading)||0));refreshRoster();});
 root.querySelector('#vmct-launch-selected').addEventListener('click',function(){execute('launch',getSelected());});
 root.querySelector('#vmct-hold-selected').addEventListener('click',function(){execute('hold',getSelected());});
 root.querySelector('#vmct-recover-selected').addEventListener('click',function(){execute('recover',getSelected());});
 root.querySelector('#vmct-launch-all').addEventListener('click',function(){
  var api=command();if(!api){status('DAEDALUS COMMAND AUTHORITY OFFLINE');return;}
  var result=api.launchAll();status(result&&result.ok?'DAEDALUS // LAUNCH SEQUENCE ACCEPTED // ALL STORED CRAFT RELEASED':'DAEDALUS // PARTIAL / FAILED LAUNCH // '+JSON.stringify(result&&result.results||[]));refreshRoster();
 });
}
function render(){
 if(!root)return;
 var u=activeUnit();root.hidden=!(u&&u.id==='daedalus');
 if(!root.hidden)refreshRoster();
}
function boot(){
 create();render();
 window.addEventListener('vigil:active-unit-changed',render);
 window.addEventListener('vigil:mothership-command',function(e){var d=e&&e.detail||{};status('DAEDALUS COMMAND LOG // '+String(d.action||'COMMAND')+' // '+String(d.unit_id||'FLEET')+' // '+String(d.timestamp||''));render();});
 window.addEventListener('vigil:simulation-unit-state-changed',render);
 window.setInterval(render,900);
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();