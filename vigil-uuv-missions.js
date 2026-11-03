/* VIGIL UUV field operations: playable local missions built on the existing Pelagos survey and artifact systems. */
(function(){
'use strict';
var STORAGE_KEY='vigil-uuv-field-operations-v1';
var missions=[
 {id:'privateers',name:"PRIVATEER'S HOLD // FIELD HANDBOOK",siteId:'PEL-PRIVATEERS-HOLD',title:"Privateer's Hold Recovery",target:{x:5.5/42,y:7.5/42},evidenceId:'PEL-ARCHIVE-EXPEDITION-HANDBOOK',radius:.035,description:'Locate the collapsed sea-cave approach, run an active sonar survey until the stronghold resolves, then recover the expedition handbook into UUV-01’s locked container.',kind:'recovery'},
 {id:'daggerfall',name:'DAGGERFALL // DROWNED CITY SURVEY',siteId:'PEL-DAGGERFALL-01',title:'Daggerfall Urban Survey',target:{x:21.5/42,y:21.5/42},evidenceId:'PEL-ARCHIVE-CHRONICLES',radius:.04,coverageRadius:.045,coverageRequired:18,description:'Chart the drowned village footprint. Build a real local coverage patch around the settlement, resolve the village on sonar, and recover the Chronicle of the Iliac Sites.',kind:'mapping'},
 {id:'rift',name:'ABYSSAL RIFT // GEOPHYSICAL TRANSECT',title:'Abyssal Rift Transect',target:{x:.23,y:.79},radius:.045,coverageRadius:.055,coverageRequired:45,sweepsRequired:2,description:'Hold a safe survey position over the crustal breach. Complete two full 360° sonar passes and map enough of the rift corridor to establish a repeatable geophysical transect.',kind:'rift'}
];
function boot(){
 var view=document.getElementById('vigil-3d-seafloor-view');
 if(!view||!view.querySelector('#vigil-3d-terrain'))return false;
 if(view.querySelector('#v3-mission-ops'))return true;
 var css=document.createElement('style');
 css.textContent='#vigil-3d-seafloor-view .v3-mission-ops{flex:0 0 auto;margin:8px 10px;padding:10px;border:1px solid #34734f;background:linear-gradient(135deg,rgba(7,31,19,.98),rgba(2,12,8,.98));color:#c9f1d7;font:11px/1.45 Courier New,monospace}#vigil-3d-seafloor-view .v3-mission-head{display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap;color:#9bf0b9;letter-spacing:1px;font-weight:bold}#vigil-3d-seafloor-view .v3-mission-select{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;align-items:center;margin:8px 0}#vigil-3d-seafloor-view .v3-mission-select select{width:100%;min-width:0;padding:9px;background:#020907;color:#d9f8e4;border:1px solid #397b58;font:11px Courier New}#vigil-3d-seafloor-view .v3-mission-summary{color:#a5d9b8;margin:6px 0 9px;line-height:1.5}#vigil-3d-seafloor-view .v3-mission-stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;margin:7px 0}#vigil-3d-seafloor-view .v3-mission-stat{padding:7px;border:1px solid #214e36;background:#020a06;min-width:0}#vigil-3d-seafloor-view .v3-mission-stat b{display:block;color:#baf5d0;font-size:13px;font-variant-numeric:tabular-nums}#vigil-3d-seafloor-view .v3-mission-stat span{display:block;color:#76a98a;font-size:8px;letter-spacing:.7px;margin-top:2px}#vigil-3d-seafloor-view .v3-mission-progress{height:7px;background:#10251a;border:1px solid #285b42;overflow:hidden;margin:7px 0}#vigil-3d-seafloor-view .v3-mission-progress span{display:block;height:100%;width:0;background:linear-gradient(90deg,#258654,#83f2b0);transition:width .18s ease}#vigil-3d-seafloor-view .v3-mission-steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:5px;margin:8px 0;padding:0;list-style:none}#vigil-3d-seafloor-view .v3-mission-steps li{padding:6px 8px;border:1px solid #1d4932;background:#020a06;color:#85b99a;font-size:10px}#vigil-3d-seafloor-view .v3-mission-steps li.done{border-color:#3e9b67;color:#c1f6d1;background:#082216}#vigil-3d-seafloor-view .v3-mission-actions{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}#vigil-3d-seafloor-view .v3-mission-actions button{min-height:35px;padding:7px 10px;font-size:10px}#vigil-3d-seafloor-view .v3-mission-actions button:disabled{opacity:.38;cursor:not-allowed}#vigil-3d-seafloor-view .v3-mission-status{margin-top:7px;padding:7px 8px;border-left:3px solid #52bd83;background:#03140b;color:#b7eac9;font-size:10px}#vigil-3d-seafloor-view .v3-mission-status.warn{border-left-color:#d6ad5b;color:#f1d79b}#vigil-3d-seafloor-view .v3-mission-note{margin-top:6px;color:#739f84;font-size:9px}@media(max-width:540px){#vigil-3d-seafloor-view .v3-mission-steps{grid-template-columns:1fr}#vigil-3d-seafloor-view .v3-mission-stat b{font-size:11px}#vigil-3d-seafloor-view .v3-mission-select{grid-template-columns:1fr}}';
 document.head.appendChild(css);
 var board=document.createElement('section');
 board.id='v3-mission-ops';board.className='v3-mission-ops';board.setAttribute('aria-label','UUV playable field missions');
 board.innerHTML='<div class="v3-mission-head"><span>FIELD OPERATIONS // PELAGOS-01</span><span id="v3-mission-serial">LOCAL SIM // NO SERVER REQUIRED</span></div><div class="v3-mission-select"><label for="v3-mission-select">ACTIVE MISSION</label><select id="v3-mission-select" aria-label="Select UUV field mission"></select></div><div id="v3-mission-title" class="v3-mission-head"></div><p id="v3-mission-description" class="v3-mission-summary"></p><div class="v3-mission-stats"><div class="v3-mission-stat"><b id="v3-mission-range">—</b><span>RANGE TO OBJECTIVE</span></div><div class="v3-mission-stat"><b id="v3-mission-coverage">0</b><span>LOCAL MAPPED CELLS</span></div><div class="v3-mission-stat"><b id="v3-mission-sweeps">0 / 0</b><span>COMPLETED SWEEPS</span></div></div><div class="v3-mission-progress" role="progressbar" aria-label="Mission objective completion" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0"><span id="v3-mission-progress-fill"></span></div><ol id="v3-mission-steps" class="v3-mission-steps"></ol><div class="v3-mission-actions"><button type="button" id="v3-mission-course" class="v3-primary">SET COURSE TO OBJECTIVE</button><button type="button" id="v3-mission-hold">HOLD POSITION</button><button type="button" id="v3-mission-scan" class="v3-primary">START SURVEY</button><button type="button" id="v3-mission-recover" disabled>RECOVER ARCHIVE</button><button type="button" id="v3-mission-restart">RESTART OBJECTIVE</button></div><div id="v3-mission-status" class="v3-mission-status" role="status" aria-live="polite">MISSION SYSTEM INITIALIZING</div><div class="v3-mission-note">MISSIONS USE THE LIVE UUV-01 MOVEMENT MODEL, PELAGOS TERRAIN, SURVEY COVERAGE AND UNIQUE ARTIFACT CUSTODY. ALL PROGRESS SAVES IN THIS BROWSER.</div>';
 var anchor=view.querySelector('#v3-world-map-panel');
 if(anchor&&anchor.parentNode)anchor.parentNode.insertBefore(board,anchor.nextSibling);else view.insertBefore(board,view.querySelector('.v3-helm'));
 var select=board.querySelector('#v3-mission-select');
 missions.forEach(function(m){var option=document.createElement('option');option.value=m.id;option.textContent=m.name;select.appendChild(option);});
 function getSurvey(){try{return typeof window.vigilGetLocalSeafloorSurveyState==='function'?window.vigilGetLocalSeafloorSurveyState():{scanning:false,sweepCount:0,coverageKeys:[],discoveries:[]};}catch(e){return {scanning:false,sweepCount:0,coverageKeys:[],discoveries:[]};}}
 function getUnit(){return typeof window.vigilGetRegionalSimulationUnit==='function'?window.vigilGetRegionalSimulationUnit('submersible'):null;}
 var survey=getSurvey(),saved={active:'privateers',baseline:{},completed:{}};
 try{var parsed=JSON.parse(window.localStorage.getItem(STORAGE_KEY)||'null');if(parsed&&parsed.version===1){saved.active=missions.some(function(m){return m.id===parsed.active;})?parsed.active:'privateers';saved.baseline=parsed.baseline&&typeof parsed.baseline==='object'?parsed.baseline:{};saved.completed=parsed.completed&&typeof parsed.completed==='object'?parsed.completed:{ };}}catch(e){}
 var activeId=saved.active;
 if(!Number.isFinite(Number(saved.baseline[activeId])))saved.baseline[activeId]=Number(survey.sweepCount)||0;
 function currentMission(){return missions.find(function(m){return m.id===activeId;})||missions[0];}
 function persist(){try{window.localStorage.setItem(STORAGE_KEY,JSON.stringify({version:1,active:activeId,baseline:saved.baseline,completed:saved.completed,updatedAt:new Date().toISOString()}));}catch(e){}}
 function distanceTo(m,u){if(!u||typeof window.vigilGetPlanetRangeBearing!=='function')return Infinity;var d=window.vigilGetPlanetRangeBearing(Number(u.x),Number(u.y),m.target.x,m.target.y);return Number(d&&d.distance);}
 function bearingTo(m,u){var d=window.vigilGetPlanetRangeBearing(Number(u.x),Number(u.y),m.target.x,m.target.y);return (Math.atan2(Number(d.east)||0,Number(d.north)||0)*180/Math.PI+360)%360;}
 function coverageNear(m,state){var r=m.coverageRadius||.04;return (state.coverageKeys||[]).reduce(function(total,key){var xy=String(key).split(':');if(xy.length!==2)return total;var x=Number(xy[0])/500,y=Number(xy[1])/500;return total+(Math.hypot(x-m.target.x,y-m.target.y)<=r?1:0);},0);}
 function artifact(m){if(!m.evidenceId||typeof window.vigilGetHistoricalEvidenceInventory!=='function')return null;return window.vigilGetHistoricalEvidenceInventory().find(function(item){return item.id===m.evidenceId;})||null;}
 function siteFound(m,state){return !!m.siteId&&(state.discoveries||[]).some(function(d){return d&&d.id===m.siteId;});}
 function evaluate(m,u,state){
  var distance=distanceTo(m,u),near=distance<=m.radius,found=siteFound(m,state),mapped=coverageNear(m,state),item=artifact(m),carried=!!(item&&item.status==='CARRIED'&&item.carrierId==='UUV-01'),baseline=Number(saved.baseline[m.id])||0,sweeps=Math.max(0,(Number(state.sweepCount)||0)-baseline),terrain=typeof window.vigilGetWorldTerrainAt==='function'?window.vigilGetWorldTerrainAt(m.target.x,m.target.y):null;
  if(m.kind==='rift'){
   var anomaly=!!(terrain&&(Number(terrain.riftCore)>.08||Number(terrain.riftWall)>.25));
   var steps=[{label:'Navigate to the mapped crustal breach',done:near},{label:'Confirm the rift signature in the simulated terrain model',done:anomaly&&near},{label:'Complete '+m.sweepsRequired+' full rotating sonar transects',done:sweeps>=m.sweepsRequired},{label:'Map at least '+m.coverageRequired+' local cells across the rift corridor',done:mapped>=m.coverageRequired}];
   return {near:near,found:anomaly,mapped:mapped,sweeps:sweeps,item:null,steps:steps,complete:steps.every(function(s){return s.done;}),distance:distance,anomaly:anomaly,baseline:baseline};
  }
  var steps=[{label:'Pilot UUV-01 to '+m.title,done:near},{label:'Run sonar until '+(m.siteId==='PEL-PRIVATEERS-HOLD'?"Privateer's Hold":"Daggerfall")+' resolves as a site',done:found}];
  if(m.kind==='mapping')steps.push({label:'Chart at least '+m.coverageRequired+' mapped cells around the settlement',done:mapped>=m.coverageRequired});
  steps.push({label:'Recover the unique archive to UUV-01 locked custody',done:carried});
  return {near:near,found:found,mapped:mapped,sweeps:sweeps,item:item,carried:carried,steps:steps,complete:steps.every(function(s){return s.done;}),distance:distance,baseline:baseline};
 }
 function statusMessage(m,progress){
  if(saved.completed[m.id]||progress.complete)return 'MISSION COMPLETE // OBJECTIVE VERIFIED IN LOCAL SIMULATION';
  if(!progress.near)return 'TRANSIT // SET COURSE TO THE OBJECTIVE AND CLOSE TO WITHIN '+Math.round(m.radius*1500)+' SIMULATED KM';
  if(!progress.found&&m.kind!=='rift')return 'ON STATION // START THE UUV SEAFLOOR SCAN TO RESOLVE THIS SITE';
  if(m.kind==='rift'&&progress.sweeps<m.sweepsRequired)return 'RIFT STATION // KEEP THE SCANNER RUNNING THROUGH '+(m.sweepsRequired-progress.sweeps)+' MORE COMPLETE SWEEP(S)';
  if(m.kind==='mapping'&&progress.mapped<m.coverageRequired)return 'SURVEY INCOMPLETE // CONTINUE MAPPING THE LOCAL CITY FOOTPRINT';
  if(progress.item&&!progress.carried)return progress.item.status==='UNDISCOVERED'?'ARCHIVE NOT LOCATED // SCAN THE RECOVERY SITE':'RECOVERY READY // LOAD THE UNIQUE ARCHIVE INTO THE LOCKED CONTAINER';
  if(m.kind==='rift'&&progress.mapped<m.coverageRequired)return 'TRANSECT INCOMPLETE // CONTINUE THE LOCAL RIFT MAPPING PASS';
  return 'OBJECTIVES IN PROGRESS // CHECK THE REQUIRED OPERATIONS ABOVE';
 }
 function render(){
  if(!view.isConnected)return;
  survey=getSurvey();var m=currentMission(),u=getUnit(),p=evaluate(m,u,survey);
  if(p.complete&&!saved.completed[m.id]){saved.completed[m.id]=true;persist();}
  select.value=activeId;
  board.querySelector('#v3-mission-title').textContent=m.title.toUpperCase()+(saved.completed[m.id]?' // COMPLETE':'');
  board.querySelector('#v3-mission-description').textContent=m.description;
  board.querySelector('#v3-mission-range').textContent=Number.isFinite(p.distance)?(p.distance*1500).toFixed(1)+' km':'NO FIX';
  board.querySelector('#v3-mission-coverage').textContent=String(p.mapped)+(m.coverageRequired?' / '+m.coverageRequired:'');
  board.querySelector('#v3-mission-sweeps').textContent=m.kind==='rift'?p.sweeps+' / '+m.sweepsRequired:'— / —';
  var done=p.steps.filter(function(s){return s.done;}).length,pct=Math.round(done/p.steps.length*100);
  board.querySelector('#v3-mission-progress-fill').style.width=pct+'%';
  board.querySelector('.v3-mission-progress').setAttribute('aria-valuenow',String(pct));
  var list=board.querySelector('#v3-mission-steps');list.textContent='';
  p.steps.forEach(function(step){var li=document.createElement('li');li.className=step.done?'done':'';li.textContent=(step.done?'✓ ':'○ ')+step.label;list.appendChild(li);});
  board.querySelector('#v3-mission-status').textContent=statusMessage(m,p);
  board.querySelector('#v3-mission-status').classList.toggle('warn',!p.near);
  board.querySelector('#v3-mission-scan').textContent=survey.scanning?'PAUSE SURVEY':'START SURVEY';
  var collect=board.querySelector('#v3-mission-recover');collect.hidden=!m.evidenceId;collect.disabled=!(p.near&&p.found&&p.item&&p.item.status!=='CARRIED');
  collect.textContent=p.item&&p.item.status==='LOST'?'RECOVER LOST ARCHIVE':'RECOVER ARCHIVE';
  board.querySelector('#v3-mission-course').disabled=!u||p.near||!Number.isFinite(p.distance);
  board.querySelector('#v3-mission-hold').disabled=!u||Math.abs(Number(u.target_speed==null?u.speed:u.target_speed)||0)<.00001;
  var restart=board.querySelector('#v3-mission-restart');restart.disabled=!!saved.completed[m.id]&&m.kind!=='rift';restart.textContent=saved.completed[m.id]?(m.kind==='rift'?'RUN ANOTHER TRANSECT':'UNIQUE RECOVERY COMPLETE'):'RESET MISSION TIMER';
  board.querySelector('#v3-mission-serial').textContent='UUV-01 // '+(u?'LOCAL SIMULATION':'UNIT UNAVAILABLE');
 }
 select.addEventListener('change',function(){activeId=this.value;if(!Number.isFinite(Number(saved.baseline[activeId])))saved.baseline[activeId]=Number(getSurvey().sweepCount)||0;persist();render();});
 board.querySelector('#v3-mission-course').addEventListener('click',function(){
  var m=currentMission(),u=getUnit();if(!u||typeof window.vigilSetSimulationUnitState!=='function'){board.querySelector('#v3-mission-status').textContent='NAVIGATION BRIDGE UNAVAILABLE';return;}
  var heading=bearingTo(m,u),distance=distanceTo(m,u),speed=distance<.025?.004:.012;
  var result=window.vigilSetSimulationUnitState('submersible',{heading:heading,speed:speed});
  if(!result||!result.ok){board.querySelector('#v3-mission-status').textContent='COURSE ORDER REJECTED // '+String(result&&result.reason||'UNIT UNAVAILABLE');return;}
  board.querySelector('#v3-mission-status').textContent='NAVIGATION ORDER ACCEPTED // '+String(Math.round(heading)).padStart(3,'0')+'° // TARGET SPEED '+Number(result.target_speed==null?speed:result.target_speed).toFixed(3);
  render();
 });
 board.querySelector('#v3-mission-hold').addEventListener('click',function(){
  var result=window.vigilSetSimulationUnitState&&window.vigilSetSimulationUnitState('submersible',{speed:0});
  board.querySelector('#v3-mission-status').textContent=result&&result.ok?'HOLD POSITION ORDER ACCEPTED // SURVEY POSITION RETAINED':'HOLD POSITION REJECTED // '+String(result&&result.reason||'UNIT UNAVAILABLE');render();
 });
 board.querySelector('#v3-mission-scan').addEventListener('click',function(){
  var state=getSurvey(),result=window.vigilSetSeafloorSurveyActive&&window.vigilSetSeafloorSurveyActive(!state.scanning);
  if(!result||!result.ok){board.querySelector('#v3-mission-status').textContent='SURVEY COMMAND FAILED // '+String(result&&result.reason||'SCANNER CONTROL UNAVAILABLE');return;}
  render();
 });
 board.querySelector('#v3-mission-recover').addEventListener('click',function(){
  var m=currentMission(),result=window.vigilCollectHistoricalEvidence&&window.vigilCollectHistoricalEvidence(m.evidenceId,'UUV-01');
  board.querySelector('#v3-mission-status').textContent=result&&result.ok?'ARCHIVE SECURED // UNIQUE ITEM PLACED IN UUV-01 LOCKED CONTAINER':'RECOVERY DENIED // '+String(result&&result.reason||'ARTIFACT SYSTEM UNAVAILABLE');render();
 });
 board.querySelector('#v3-mission-restart').addEventListener('click',function(){
  var m=currentMission();if(saved.completed[m.id]&&m.kind!=='rift'){board.querySelector('#v3-mission-status').textContent='UNIQUE RECOVERY ALREADY VERIFIED // THIS PHYSICAL ARCHIVE CANNOT BE DUPLICATED';return;}saved.baseline[m.id]=Number(getSurvey().sweepCount)||0;delete saved.completed[m.id];persist();render();
  board.querySelector('#v3-mission-status').textContent='MISSION REINITIALIZED // WORLD SURVEY AND UNIQUE ARTIFACTS WERE NOT RESET';
 });
 view.querySelector('#v3-scan').addEventListener('click',function(){window.setTimeout(render,0);});
 ['vigil:simulation-unit-state-changed','vigil:sensor-observation','vigil:seafloor-survey-merged','vigil:historical-evidence-updated','vigil:seafloor-scan-state'].forEach(function(name){window.addEventListener(name,render);});
 render();
 var timer=window.setInterval(function(){if(view.classList.contains('open'))render();},650);
 window.addEventListener('pagehide',function(){window.clearInterval(timer);});
 return true;
}
if(!boot()){var tries=0;var timer=window.setInterval(function(){tries++;if(boot()||tries>=40)window.clearInterval(timer);},250);}
})();