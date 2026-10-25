(function () {
  'use strict';
  // Generic training profiles: finite simulation limits, not claims about specific platforms.
  var UNIT_CATALOG = [
    { id:'scout-drone', name:'Small reconnaissance drone', domain:'air', role:'ISR', speed_kmh:60, endurance_minutes:90, payload_kg:2, sensor_suite:['optical'], inventory:12, max_deployed:6, recovery_minutes:25, reliability:0.88, signature:'low', notes:'Battery and recovery constrained.' },
    { id:'long-endurance-uav', name:'Northrop Grumman RQ-4 Global Hawk (Block-specific values vary)', domain:'air', role:'strategic ISR', speed_kmh:574, endurance_minutes:2040, payload_kg:1360, sensor_suite:['electro-optical/infrared','synthetic-aperture radar','signals intelligence (variant-dependent)'], inventory:2, max_deployed:1, recovery_minutes:180, reliability:0.92, signature:'high', dimensions_m:{length:14.5,wingspan:39.8,height:4.7}, specification_source:'https://www.af.mil/About-Us/Fact-Sheets/Display/Article/104516/rq-4-global-hawk/', model_asset_url:'https://assets.science.nasa.gov/content/dam/science/cds/3d/resources/model/global-hawk/Global%20Hawk.glb', model_asset_page_url:'https://science.nasa.gov/3d-resources/global-hawk/', model_asset_format:'glb', model_asset_attribution:'NASA/Michael D. Carbajal', model_asset_license:'NASA media usage guidelines; check any third-party notices before redistribution', model_asset_status:'remote GLB preview integrated; model is hosted by NASA, not bundled in this repository', specification_confidence:'official published platform specifications; variant values differ', notes:'Scenario inventory and turnaround are VIGIL gameplay settings, not a claim about current fleet availability.' },
    { id:'mq-9a-reaper', name:'General Atomics MQ-9A Reaper (USMC Block V reference)', domain:'air', role:'ISR', speed_kmh:444, endurance_minutes:1620, payload_kg:1747, sensor_suite:['EO/IR','multi-mode radar','maritime radar','AIS','communications relay'], inventory:2, max_deployed:1, recovery_minutes:120, reliability:0.90, signature:'high', dimensions_m:{length:11,wingspan:20,height:null}, specification_source:'https://www.navair.navy.mil/product/MQ-9A-Reaper', model_asset_url:'https://sketchfab.com/models/eff549610fee4f20904f7b388a3a0830/embed', model_asset_page_url:'https://sketchfab.com/3d-models/mq-9-reaper-eff549610fee4f20904f7b388a3a0830', model_asset_format:'sketchfab-embed', model_asset_attribution:'Tyler V Howell / Sketchfab', model_asset_license:'Creative Commons Attribution; currently embedded remotely, not redistributed; verify license terms before bundling', model_asset_status:'interactive third-party model preview; remote embed, not bundled', specification_confidence:'official NAVAIR Block V page; payload combines 386 kg internal and 1361 kg external capacities', notes:'Scenario inventory and turnaround are VIGIL gameplay settings; payload is not a single interchangeable payload.' },
    { id:'manned-surveillance', name:'Manned surveillance aircraft', domain:'air', role:'ISR', speed_kmh:450, endurance_minutes:360, payload_kg:900, sensor_suite:['radar','optical'], inventory:2, max_deployed:1, recovery_minutes:90, reliability:0.94, signature:'high', notes:'Crewed sortie; finite aircraft and turnaround time.' },
    { id:'surface-patrol', name:'Surface patrol vessel', domain:'maritime', role:'patrol', speed_kmh:45, endurance_minutes:2880, payload_kg:1200, sensor_suite:['radar','optical'], inventory:4, max_deployed:3, recovery_minutes:180, reliability:0.91, signature:'high', notes:'Limited fleet and replenishment availability.' },
    { id:'subsurface-scout', name:'Subsurface scout', domain:'maritime', role:'undersea', speed_kmh:28, endurance_minutes:1440, payload_kg:300, sensor_suite:['sonar'], inventory:2, max_deployed:1, recovery_minutes:240, reliability:0.86, signature:'low', notes:'Sonar-only training profile; long turnaround.' },
    { id:'prank-submersible', name:'Phallus-class novelty submarine (BONUS / NON-CANON)', domain:'maritime', role:'comic decoy', speed_kmh:18, endurance_minutes:420, payload_kg:69, sensor_suite:['sonar','ridiculously loud novelty horn'], inventory:1, max_deployed:1, recovery_minutes:69, reliability:0.69, signature:'unmistakable', is_bonus:true, silhouette:'deliberately phallic cartoon submarine', model_asset_url:'vigil/assets/phallus-class.gltf', model_asset_page_url:'vigil/assets/phallus-class.gltf', model_asset_format:'gltf', model_asset_attribution:'Original procedural VIGIL bonus asset', model_asset_license:'Original project-generated geometry', model_asset_status:'local procedural 3D gag model; bundled in repository', notes:'JOKE BONUS UNIT ONLY: intentionally phallic silhouette and silly stats; entirely fictional, not a real vessel or performance reference.' },
    { id:'ground-sensor-team', name:'Mobile ground sensor team', domain:'ground', role:'sensor', speed_kmh:8, endurance_minutes:480, payload_kg:35, sensor_suite:['optical'], inventory:6, max_deployed:4, recovery_minutes:30, reliability:0.9, signature:'medium', notes:'Limited team count and operating duration.' }
  ];
  var SCENARIOS = [
    { id:'level-1', name:'01 / SENSOR FAMILIARIZATION', difficulty:'INTRODUCTORY', objective:'Learn sensor modes, contact classification, and uncertainty.', unitIds:['scout-drone','ground-sensor-team'], activeContacts:3, detectionNoise:'LOW', unlock:'Available at start.' },
    { id:'level-2', name:'02 / RECONNAISSANCE', difficulty:'STANDARD', objective:'Investigate ambiguous contacts with limited sensor endurance.', unitIds:['scout-drone','long-endurance-uav','ground-sensor-team'], activeContacts:6, detectionNoise:'MODERATE', unlock:'Complete Level 1.' },
    { id:'level-3', name:'03 / MULTI-UNIT OPERATIONS', difficulty:'ADVANCED', objective:'Balance air, maritime, and ground assets while maintaining tracks.', unitIds:['scout-drone','long-endurance-uav','mq-9a-reaper','manned-surveillance','surface-patrol','ground-sensor-team'], activeContacts:10, detectionNoise:'VARIABLE', unlock:'Complete Level 2.' },
    { id:'level-4', name:'04 / DEGRADED SENSORS', difficulty:'EXPERT', objective:'Handle clutter, intermittent detection, stale tracks, and conflicting evidence.', unitIds:['scout-drone','long-endurance-uav','mq-9a-reaper','surface-patrol','subsurface-scout','ground-sensor-team'], activeContacts:14, detectionNoise:'HIGH / INTERMITTENT', unlock:'Complete Level 3.' },
    { id:'level-5', name:'05 / NETWORKED OPERATIONS', difficulty:'MULTI-ROLE', objective:'Coordinate distinct intelligence pictures and explicit information-sharing rules.', unitIds:['scout-drone','long-endurance-uav','mq-9a-reaper','manned-surveillance','surface-patrol','subsurface-scout','ground-sensor-team','prank-submersible'], activeContacts:20, detectionNoise:'SCENARIO-DEFINED', unlock:'Complete Level 4; multiplayer transport is a planned milestone.' }
  ];
  var state = { levelId:'level-1', clockMinutes:0, sorties:[], nextSortieId:1, sharedIntelOptIn:false, log:[] };
  // Player-visible intelligence is a separate, allow-listed store. Hidden scenario truth
  // belongs to the simulation/evaluator and is intentionally not part of this browser API.
  var playerPictures = Object.create(null);
  var playerSharing = Object.create(null);
  var OBSERVATION_FIELDS = ['contactId','observedAt','positionEstimate','classificationEstimate','confidence','modality','uncertaintyMeters','status','sourceUnitId','sourceObservations','conflict','conflictDistanceMeters','trackRevision'];
  function cleanObservation(input) {
    if (!input || typeof input !== 'object' || typeof input.contactId !== 'string' || !input.contactId) return null;
    var out = {};
    OBSERVATION_FIELDS.forEach(function(key) {
      if (input[key] === undefined) return;
      if (key === 'positionEstimate' && input[key] && typeof input[key] === 'object') {
        var p = input[key], pos = {};
        ['x','y','z'].forEach(function(axis) { if (Number.isFinite(p[axis])) pos[axis] = p[axis]; });
        if (Object.keys(pos).length) out.positionEstimate = pos;
      } else if (key === 'confidence') {
        if (Number.isFinite(input[key])) out.confidence = Math.max(0, Math.min(1, input[key]));
      } else if (key === 'uncertaintyMeters') {
        if (Number.isFinite(input[key]) && input[key] >= 0) out.uncertaintyMeters = input[key];
      } else if (key === 'observedAt') {
        if (Number.isFinite(input[key])) out.observedAt = input[key];
      } else if (typeof input[key] === 'string' || typeof input[key] === 'boolean') out[key] = input[key];
    });
    out.status = out.status || 'CURRENT';
    out.confidence = Number.isFinite(out.confidence) ? out.confidence : 0.5;
    out.uncertaintyMeters = Number.isFinite(out.uncertaintyMeters) ? out.uncertaintyMeters : null;
    return out;
  }
  function fuseObservation(playerId, observation, options) {
    options = options || {};
    var clean = cleanObservation(observation);
    if (!clean) return {ok:false,reason:'invalid_observation'};
    var picture = playerPictures[playerId] || (playerPictures[playerId] = Object.create(null));
    var previous = picture[clean.contactId];
    var threshold = Number.isFinite(options.conflictThreshold) ? Math.max(0, options.conflictThresholdMeters) : 0.18;
    var distance = null, conflict = false;
    if (previous && previous.positionEstimate && clean.positionEstimate) {
      var a = previous.positionEstimate, b = clean.positionEstimate;
      var dx = Number(a.x||0)-Number(b.x||0), dy = Number(a.y||0)-Number(b.y||0), dz = Number(a.z||0)-Number(b.z||0);
      distance = Math.sqrt(dx*dx+dy*dy+dz*dz);
      conflict = distance > threshold;
    }
    var sourceList = previous && Array.isArray(previous.sourceObservations) ? previous.sourceObservations.slice() : [];
    sourceList.push({
      observedAt: clean.observedAt,
      positionEstimate: clean.positionEstimate ? JSON.parse(JSON.stringify(clean.positionEstimate)) : null,
      confidence: clean.confidence,
      uncertaintyMeters: clean.uncertaintyMeters,
      modality: clean.modality || 'unknown',
      sourceUnitId: clean.sourceUnitId || 'unknown'
    });
    if (sourceList.length > 8) sourceList = sourceList.slice(-8);
    if (previous && previous.positionEstimate && clean.positionEstimate && !conflict) {
      var oldU = Number(previous.uncertaintyMeters), newU = Number(clean.uncertaintyMeters);
      var oldWeight = Number.isFinite(oldU) && oldU > 0 ? 1/(oldU*oldU) : 1;
      var newWeight = Number.isFinite(newU) && newU > 0 ? 1/(newU*newU) : 1;
      var denom = oldWeight + newWeight, fused = {};
      ['x','y','z'].forEach(function(axis) {
        fused[axis] = ((Number(previous.positionEstimate[axis]||0)*oldWeight)+(Number(clean.positionEstimate[axis]||0)*newWeight))/denom;
      });
      clean.positionEstimate = fused;
      clean.uncertaintyMeters = Math.sqrt(1/denom);
      clean.confidence = Math.max(previous.confidence||0,clean.confidence||0);
    } else if (conflict && previous) {
      clean.positionEstimate = JSON.parse(JSON.stringify(previous.positionEstimate));
      clean.uncertaintyMeters = Math.max(Number(previous.uncertaintyMeters)||0,Number(clean.uncertaintyMeters)||0,distance||0);
      clean.confidence = Math.min(Number(previous.confidence)||0.5,Number(clean.confidence)||0.5);
    }
    clean.sourceObservations = sourceList;
    clean.conflict = conflict;
    clean.conflictDistance = distance;
    clean.trackRevision = (previous && Number(previous.trackRevision)||0)+1;
    clean.status = conflict ? 'CONFLICT' : 'CURRENT';
    picture[clean.contactId] = clean;
    return {ok:true,observation:JSON.parse(JSON.stringify(clean)),conflict:conflict,distance:distance};
  }
  function recordObservation(playerId, observation) {
    if (typeof playerId !== 'string' || !playerId.trim()) return {ok:false,reason:'invalid_player'};
    var clean = cleanObservation(observation);
    if (!clean) return {ok:false,reason:'invalid_observation'};
    var picture = playerPictures[playerId] || (playerPictures[playerId] = Object.create(null));
    var previous = picture[clean.contactId];
    if (previous && Number.isFinite(previous.observedAt) && Number.isFinite(clean.observedAt) && clean.observedAt < previous.observedAt) {
      return {ok:false,reason:'older_observation'};
    }
    picture[clean.contactId] = clean;
    return {ok:true,observation:JSON.parse(JSON.stringify(clean))};
  }
  function getPlayerPicture(playerId) {
    var picture = playerPictures[playerId] || Object.create(null);
    return Object.keys(picture).map(function(id) {
      var item = JSON.parse(JSON.stringify(picture[id]));
      if (Number.isFinite(item.observedAt) && state.clockMinutes - item.observedAt > 30 && (item.status === 'CURRENT' || item.status === 'LAST_KNOWN')) item.status = 'STALE';
      return item;
    });
  }
  function markUnobserved(playerId, observedContactIds) {
    if (typeof playerId !== 'string' || !playerId.trim()) return {ok:false,reason:'invalid_player'};
    var picture = playerPictures[playerId] || (playerPictures[playerId] = Object.create(null));
    var visible = Object.create(null);
    (Array.isArray(observedContactIds) ? observedContactIds : []).forEach(function(id) {
      if (typeof id === 'string') visible[id] = true;
    });
    var aged = [];
    Object.keys(picture).forEach(function(id) {
      var item = picture[id];
      if (!visible[id] && item.status === 'CURRENT') {
        item.status = 'LAST_KNOWN';
        aged.push(id);
      }
    });
    return {ok:true,agedContactIds:aged};
  }
  function setIntelSharing(playerId, enabled) {
    if (typeof playerId !== 'string' || !playerId.trim() || typeof enabled !== 'boolean') return {ok:false,reason:'invalid_policy'};
    playerSharing[playerId] = enabled;
    return {ok:true,enabled:enabled};
  }
  function shareObservation(fromPlayerId, toPlayerId, contactId) {
    if (!playerSharing[fromPlayerId] || !playerSharing[toPlayerId]) return {ok:false,reason:'sharing_not_mutually_enabled'};
    var source = playerPictures[fromPlayerId];
    var observation = source && source[contactId];
    if (!observation) return {ok:false,reason:'observation_not_found'};
    var shared = JSON.parse(JSON.stringify(observation));
    shared.status = 'SHARED';
    shared.sharedBy = fromPlayerId;
    var target = playerPictures[toPlayerId] || (playerPictures[toPlayerId] = Object.create(null));
    target[contactId] = shared;
    return {ok:true,observation:JSON.parse(JSON.stringify(shared))};
  }
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
      return '<article class="sim-recon-contact" data-unit-id="'+safe(u.id)+'" style="border:1px solid var(--line);padding:.65rem;border-radius:6px"><strong>'+safe(u.name)+'</strong><br><span class="muted">'+safe(u.domain.toUpperCase())+' / '+safe(u.role)+'</span><br>Speed: '+u.speed_kmh+' km/h · Endurance: '+u.endurance_minutes+' min<br>Payload: '+u.payload_kg+' kg · Sensors: '+safe(u.sensor_suite.join(', '))+'<br>Fleet: '+u.inventory+' · Ready: '+readyCount+' · Active: '+a+' · Recovering: '+r+'<br>Sortie endurance remaining: '+activeText+'<br>Max active: '+u.max_deployed+' · Turnaround: '+u.recovery_minutes+' min · Reliability: '+Math.round(u.reliability*100)+'%<br>Signature: '+safe(u.signature.toUpperCase())+'<br>Model: '+safe(u.model_asset_status||'generic training profile')+'<br>Specs: '+(u.specification_source?'<a href="'+safe(u.specification_source)+'" target="_blank" rel="noopener noreferrer">source</a>':'not sourced')+' · Geometry: '+(u.model_asset_url?'<a href="'+safe(u.model_asset_page_url||u.model_asset_url)+'" target="_blank" rel="noopener noreferrer">model source</a>':'not sourced')+((u.model_asset_format==='glb'||u.model_asset_format==='gltf')?'<br><div class="sim-model-stage" style="position:relative;margin:.55rem 0"><model-viewer src="'+safe(u.model_asset_url)+'" alt="'+safe(u.name)+' 3D model" camera-controls auto-rotate loading="lazy" shadow-intensity="1" style="display:block;width:100%;height:190px;background:#04130f;border:1px solid var(--line);border-radius:4px"></model-viewer>'+(u.id==='prank-submersible'&&window.vigilPhallusTrophyUnlocked?'<div class="phallus-victory-plaque" data-victory-plaque="phallus" style="position:absolute;left:50%;top:52%;transform:translate(-50%,-50%) rotate(-5deg);z-index:2;padding:.45rem .6rem;border:2px solid #ffd700;border-radius:5px;background:rgba(12,28,19,.94);color:#ffe56b;text-align:center;font-size:clamp(10px,2.2vw,14px);font-weight:1000;letter-spacing:.035em;text-shadow:0 0 7px #ffca28;box-shadow:0 0 12px #ffd70088;pointer-events:none;white-space:nowrap">🥇 I GOT MY DICK BACK</div>':'')+'</div><small class="muted">3D ASSET: '+safe(u.model_asset_attribution||'source attribution pending')+' · '+(u.model_asset_format==='gltf'?'LOCAL MODEL · BUNDLED':'REMOTE LOAD · NOT BUNDLED')+'</small>':u.model_asset_format==='sketchfab-embed'?'<br><iframe title="'+safe(u.name)+' interactive 3D model" src="'+safe(u.model_asset_url)+'" loading="lazy" allow="autoplay; fullscreen; xr-spatial-tracking" allowfullscreen style="display:block;width:100%;height:230px;margin:.55rem 0;border:1px solid var(--line);border-radius:4px;background:#04130f"></iframe><small class="muted">3D ASSET: '+safe(u.model_asset_attribution||'source attribution pending')+' · '+safe(u.model_asset_license||'license details pending')+' · REMOTE EMBED · NOT BUNDLED</small>':'')+'<br><span class="muted">'+safe(u.notes)+'</span><br><button type="button" data-deploy-unit="'+safe(u.id)+'" '+(readyCount<=0||a>=u.max_deployed?'disabled':'')+'>DEPLOY UNIT</button> <button type="button" data-recover-unit="'+safe(u.id)+'" '+(a<=0?'disabled':'')+'>RECOVER / RELEASE</button><span class="muted" data-unit-status="'+safe(u.id)+'" aria-live="polite"></span></article>';
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
    var api=window.vigilSimulationCatalog,picture=api&&api.getPlayerPicture?api.getPlayerPicture('vigil'):[],lastKnown=picture.filter(function(item){return item.status==='LAST_KNOWN';}).length,stale=picture.filter(function(item){return item.status==='STALE';}).length;
    el('sim-fow-status').textContent='FOG OF WAR // PLAYER OBSERVATION VIEW\nCURRENT OBSERVED CONTACTS: '+n+'\nLAST-KNOWN TRACKS: '+lastKnown+' · STALE TRACKS: '+stale+'\nGROUND TRUTH: NOT EXPOSED TO PLAYER-FACING POLICY\nTRACK RULE: DISAPPEARING CONTACTS SHOULD AGE TO LAST-KNOWN / STALE, NOT BE ASSUMED DESTROYED\nINTELLIGENCE SHARING: PLAYER-SCOPED PERMISSION REQUIRED; THIS LOCAL PROTOTYPE DOES NOT BROADCAST DATA.';
  }
  function init(){
    try{window.vigilPhallusTrophyUnlocked=window.localStorage.getItem('vigil-phallus-victory-trophy-v1')==='true';}catch(e){window.vigilPhallusTrophyUnlocked=false;}
    window.addEventListener('vigil:game-victory',function(){window.vigilPhallusTrophyUnlocked=true;try{window.localStorage.setItem('vigil-phallus-victory-trophy-v1','true');}catch(e){}renderLevel();});
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
      observeFow:function(observations){return {observed_contact_count:Array.isArray(observations)?observations.length:0,ground_truth_included:false,information_scope:'authorized_observations_only'};},
      recordObservation:recordObservation,
      fuseObservation:fuseObservation,
      markUnobserved:markUnobserved,
      getPlayerPicture:getPlayerPicture,
      setIntelSharing:setIntelSharing,
      shareObservation:shareObservation
    };
    window.dispatchEvent(new CustomEvent('vigil:fow-ready'));
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();