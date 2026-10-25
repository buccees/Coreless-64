(function () {
  'use strict';
  // Generic training profiles: finite simulation limits, not claims about specific platforms.
  var UNIT_CATALOG = [
    { id:'scout-drone', name:'Small reconnaissance drone', domain:'air', role:'ISR', speed_kmh:60, endurance_minutes:90, payload_kg:2, sensor_suite:['optical'], inventory:12, max_deployed:6, recovery_minutes:25, reliability:0.88, signature:'low', notes:'Battery and recovery constrained.' },
    { id:'long-endurance-uav', name:'Long-endurance unmanned aircraft', domain:'air', role:'ISR', speed_kmh:180, endurance_minutes:720, payload_kg:150, sensor_suite:['radar','optical'], inventory:3, max_deployed:2, recovery_minutes:60, reliability:0.92, signature:'medium', notes:'Small fleet; maintenance and payload limits apply.' },
    { id:'manned-surveillance', name:'Manned surveillance aircraft', domain:'air', role:'ISR', speed_kmh:450, endurance_minutes:360, payload_kg:900, sensor_suite:['radar','optical'], inventory:2, max_deployed:1, recovery_minutes:90, reliability:0.94, signature:'high', notes:'Crewed sortie; finite aircraft and turnaround time.' },
    { id:'surface-patrol', name:'Surface patrol vessel', domain:'maritime', role:'patrol', speed_kmh:45, endurance_minutes:2880, payload_kg:1200, sensor_suite:['radar','optical'], inventory:4, max_deployed:3, recovery_minutes:180, reliability:0.91, signature:'high', notes:'Limited fleet and replenishment availability.' },
    { id:'subsurface-scout', name:'Subsurface scout', domain:'maritime', role:'undersea', speed_kmh:28, endurance_minutes:1440, payload_kg:300, sensor_suite:['sonar'], inventory:2, max_deployed:1, recovery_minutes:240, reliability:0.86, signature:'low', notes:'Sonar-only training profile; long turnaround.' },
    { id:'ground-sensor-team', name:'Mobile ground sensor team', domain:'ground', role:'sensor', speed_kmh:8, endurance_minutes:480, payload_kg:35, sensor_suite:['optical'], inventory:6, max_deployed:4, recovery_minutes:30, reliability:0.9, signature:'medium', notes:'Limited team count and operating duration.' }
  ];
  var SCENARIOS = [
    { id:'level-1', name:'01 / SENSOR FAMILIARIZATION', difficulty:'INTRODUCTORY', objective:'Learn sensor modes, contact classification, and uncertainty.', unitIds:['scout-drone','ground-sensor-team'], activeContacts:3, detectionNoise:'LOW', unlock:'Available at start.' },
    { id:'level-2', name:'02 / RECONNAISSANCE', difficulty:'STANDARD', objective:'Investigate ambiguous contacts with limited sensor endurance.', unitIds:['scout-drone','long-endurance-uav','ground-sensor-team'], activeContacts:6, detectionNoise:'MODERATE', unlock:'Complete Level 1.' },
    { id:'level-3', name:'03 / MULTI-UNIT OPERATIONS', difficulty:'ADVANCED', objective:'Balance air, maritime, and ground assets while maintaining tracks.', unitIds:['scout-drone','long-endurance-uav','manned-surveillance','surface-patrol','ground-sensor-team'], activeContacts:10, detectionNoise:'VARIABLE', unlock:'Complete Level 2.' },
    { id:'level-4', name:'04 / DEGRADED SENSORS', difficulty:'EXPERT', objective:'Handle clutter, intermittent detection, stale tracks, and conflicting evidence.', unitIds:['scout-drone','long-endurance-uav','surface-patrol','subsurface-scout','ground-sensor-team'], activeContacts:14, detectionNoise:'HIGH / INTERMITTENT', unlock:'Complete Level 3.' },
    { id:'level-5', name:'05 / NETWORKED OPERATIONS', difficulty:'MULTI-ROLE', objective:'Coordinate distinct intelligence pictures and explicit information-sharing rules.', unitIds:['scout-drone','long-endurance-uav','manned-surveillance','surface-patrol','subsurface-scout','ground-sensor-team'], activeContacts:20, detectionNoise:'SCENARIO-DEFINED', unlock:'Complete Level 4; multiplayer transport is a planned milestone.' }
  ];
  var state = { levelId:'level-1', clockMinutes:0, sorties:[], nextSortieId:1, sharedIntelOptIn:false, log:[] };
  function byId(list,id){return list.find(function(item){return item.id===id;});}
  function el(id){return document.getElementById(id);}
  function safe(value){return String(value).replace(/[&<>"]/g,function(ch){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[ch];});}
  function active(id){return state.sorties.filter(function(s){return s.unitId===id&&s.status==='DEPLOYED';});}
  function recovering(id){return state.sorties.filter(function(s){return s.unitId===id&&s.status==='RECOVERING';});}
  function totalUnavailable(id){return state.sorties.filter(function(s){return s.unitId===id&&s.status!=='READY';}).length;}
  function ready(id){return byId(UNIT_CATALOG,id).inventory-totalUnavailable(id);}
  function note(message){state.log.unshift('T+'+state.clockMinutes+' MIN // '+message);state.log=state.log.slice(0,8);}
  function renderClock(){
    var out=el('sim-clock-status');if(!out)return;
    out.textContent='MISSION CLOCK: T+'+state.clockMinutes+' MIN\nACTIVE SORTIES: '+state.sorties.filter(function(s){return s.status==='DEPLOYED';}).length+'\nRECOVERING / TURNAROUND: '+state.sorties.filter(function(s){return s.status==='RECOVERING';}).length+'\n'+(state.log[0]||'READY // DEPLOY A UNIT TO BEGIN');
  }
  function renderLevel(){
    var level=byId(SCENARIOS,state.levelId);
    el('sim-level-brief').textContent=level.name+'\nDIFFICULTY: '+level.difficulty+'\nOBJECTIVE: '+level.objective+'\nSIMULATED CONTACT SCALE: '+level.activeContacts+'\nSENSOR CONDITIONS: '+level.detectionNoise+'\nPROGRESSION: '+level.unlock;
    el('sim-unit-roster').innerHTML=level.unitIds.map(function(id){
      var u=byId(UNIT_CATALOG,id), sorties=state.sorties.filter(function(s){return s.unitId===id;}), a=active(id).length, r=recovering(id).length, readyCount=ready(id);
      var remaining=sorties.filter(function(s){return s.status==='DEPLOYED';}).map(function(s){return s.remainingMinutes;});
      var activeText=remaining.length?remaining.map(function(v){return v+'m'}).join(', '):'—';
      return '<article class="sim-recon-contact" data-unit-id="'+safe(u.id)+'" style="border:1px solid var(--line);padding:.65rem;border-radius:6px"><strong>'+safe(u.name)+'</strong><br><span class="muted">'+safe(u.domain.toUpperCase())+' / '+safe(u.role)+'</span><br>Speed: '+u.speed_kmh+' km/h · Endurance: '+u.endurance_minutes+' min<br>Payload: '+u.payload_kg+' kg · Sensors: '+safe(u.sensor_suite.join(', '))+'<br>Fleet: '+u.inventory+' · Ready: '+readyCount+' · Active: '+a+' · Recovering: '+r+'<br>Sortie endurance remaining: '+activeText+'<br>Max active: '+u.max_deployed+' · Turnaround: '+u.recovery_minutes+' min · Reliability: '+Math.round(u.reliability*100)+'%<br>Signature: '+safe(u.signature.toUpperCase())+'<br><span class="muted">'+safe(u.notes)+'</span><br><button type="button" data-deploy-unit="'+safe(u.id)+'" '+(readyCount<=0||a>=u.max_deployed?'disabled':'')+'>DEPLOY UNIT</button> <button type="button" data-recover-unit="'+safe(u.id)+'" '+(a<=0?'disabled':'')+'>RECOVER / RELEASE</button><span class="muted" data-unit-status="'+safe(u.id)+'" aria-live="polite"></span></article>';
    }).join('');
    el('sim-unit-roster').querySelectorAll('[data-deploy-unit]').forEach(function(button){button.addEventListener('click',function(){
      var result=deploy(this.getAttribute('data-deploy-unit'));
      var status=el('sim-unit-roster').querySelector('[data-unit-status="'+this.getAttribute('data-deploy-unit')+'"]');
      if(status)status.textContent=result.ok?' // SORTIE STARTED; ENDURANCE CLOCK RUNNING':' // DEPLOY REJECTED: '+result.reason;
    });});
    el('sim-unit-roster').querySelectorAll('[data-recover-unit]').forEach(function(button){button.addEventListener('click',function(){
      var result=recover(this.getAttribute('data-recover-unit'));
      var status=el('sim-unit-roster').querySelector('[data-unit-status="'+this.getAttribute('data-recover-unit')+'"]');
      if(status)status.textContent=result.ok?' // RECOVERED; TURNAROUND TIMER STARTED':' // RECOVERY REJECTED: '+result.reason;
    });});
    renderClock();
  }
  function deploy(id){
    var u=byId(UNIT_CATALOG,id);if(!u)return {ok:false,reason:'unknown_unit'};
    if(ready(id)<=0)return {ok:false,reason:'fleet_unavailable'};
    if(active(id).length>=u.max_deployed)return {ok:false,reason:'deployment_capacity'};
    var sortie={sortieId:state.nextSortieId++,unitId:id,status:'DEPLOYED',remainingMinutes:u.endurance_minutes,recoveryRemaining:0,launchedAt:state.clockMinutes};
    state.sorties.push(sortie);note(u.name+' sortie '+sortie.sortieId+' deployed.');renderLevel();
    return {ok:true,sortieId:sortie.sortieId,remaining:ready(id),endurance_minutes:sortie.remainingMinutes};
  }
  function recover(id){
    var s=active(id)[0];if(!s)return {ok:false,reason:'no_active_sortie'};
    var u=byId(UNIT_CATALOG,id);s.status='RECOVERING';s.recoveryRemaining=u.recovery_minutes;note(u.name+' sortie '+s.sortieId+' recovered; turnaround '+u.recovery_minutes+' min.');renderLevel();
    return {ok:true,recovery_minutes:s.recoveryRemaining};
  }
  function advanceTime(minutes){
    minutes=Number(minutes);
    if(!Number.isFinite(minutes)||minutes<=0||minutes>1440)return {ok:false,reason:'invalid_time_step'};
    state.clockMinutes+=minutes;
    state.sorties.forEach(function(s){
      if(s.status==='DEPLOYED'){
        s.remainingMinutes=Math.max(0,s.remainingMinutes-minutes);
        if(s.remainingMinutes===0){
          var u=byId(UNIT_CATALOG,s.unitId);s.status='RECOVERING';s.recoveryRemaining=u.recovery_minutes;
          note(u.name+' sortie '+s.sortieId+' reached endurance limit; forced recovery and turnaround started.');
        }
      } else if(s.status==='RECOVERING'){
        s.recoveryRemaining=Math.max(0,s.recoveryRemaining-minutes);
        if(s.recoveryRemaining===0){s.status='READY';note(byId(UNIT_CATALOG,s.unitId).name+' sortie '+s.sortieId+' ready after turnaround.');}
      }
    });
    renderLevel();return {ok:true,clockMinutes:state.clockMinutes,state:getState()};
  }
  function getState(){
    var deployed=Object.create(null),recoveringCounts=Object.create(null),readyCounts=Object.create(null);
    UNIT_CATALOG.forEach(function(u){deployed[u.id]=active(u.id).length;recoveringCounts[u.id]=recovering(u.id).length;readyCounts[u.id]=ready(u.id);});
    return {levelId:state.levelId,clockMinutes:state.clockMinutes,deployed:deployed,recovering:recoveringCounts,ready:readyCounts,sorties:state.sorties.map(function(s){return Object.assign({},s);}),log:state.log.slice()};
  }
  function renderFow(){
    var contacts=el('sim-recon-contacts'),n=contacts?contacts.querySelectorAll('button.sim-recon-contact').length:0;
    el('sim-fow-status').textContent='FOG OF WAR // PLAYER OBSERVATION VIEW\nCURRENT OBSERVED CONTACTS: '+n+'\nGROUND TRUTH: NOT EXPOSED TO PLAYER-FACING POLICY\nTRACK RULE: DISAPPEARING CONTACTS SHOULD AGE TO LAST-KNOWN / STALE, NOT BE ASSUMED DESTROYED\nINTELLIGENCE SHARING: PLAYER-SCOPED PERMISSION REQUIRED; THIS LOCAL PROTOTYPE DOES NOT BROADCAST DATA.';
  }
  function init(){
    var select=el('sim-level-select');if(!select)return;
    select.innerHTML=SCENARIOS.map(function(s){return '<option value="'+safe(s.id)+'">'+safe(s.name)+'</option>';}).join('');
    select.addEventListener('change',function(){state.levelId=this.value;state.clockMinutes=0;state.sorties=[];state.nextSortieId=1;state.log=[];renderLevel();});
    var advance=el('sim-advance-time');if(advance)advance.addEventListener('click',function(){advanceTime(Number(el('sim-time-step').value));});
    renderLevel();renderFow();
    var contactList=el('sim-recon-contacts');
    if(contactList&&typeof MutationObserver!=='undefined')new MutationObserver(renderFow).observe(contactList,{childList:true,subtree:true,characterData:true});
    window.vigilSimulationCatalog={
      getUnits:function(){return UNIT_CATALOG.map(function(u){return JSON.parse(JSON.stringify(u));});},
      getScenarios:function(){return SCENARIOS.map(function(s){return JSON.parse(JSON.stringify(s));});},
      getState:getState,deploy:deploy,recover:recover,advanceTime:advanceTime,
      observeFow:function(observations){return {observed_contact_count:Array.isArray(observations)?observations.length:0,ground_truth_included:false,information_scope:'authorized_observations_only'};}
    };
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();