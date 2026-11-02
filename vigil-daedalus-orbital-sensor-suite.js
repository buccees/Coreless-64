(function(){
'use strict';
var UNIT='DAEDALUS-01',VIEW_ID='vigil-daedalus-orbital-view',BUTTON_ID='vigil-daedalus-orbital-launch';
var COLS=36,ROWS=18,ORBIT_PERIOD_MS=92.6*60*1000,INCLINATION=51.6*Math.PI/180;
var samples=[],cells=[],orbitAnchor=null,orbitEpoch=0,opened=false,raf=0,lastFeedAt=0,lastDrawAt=0;
var canvas=null,ctx=null,view=null,button=null,layerState={radar:true,optical:true,thermal:true,laser:true,fusion:true,magnetic:false};
var yaw=0,pitch=0,zoom=1,drag=null,previousBodyOverflow='',lastReadoutAt=0,modelStats={radar:0,optical:0,thermal:0,laser:0,fused:0};
var LAYERS=[
 {id:'radar',label:'ORBITAL RADAR',color:'#72ffbb'},
 {id:'optical',label:'OPTICAL / MULTISPECTRAL',color:'#c7f7d9'},
 {id:'thermal',label:'IR / THERMAL',color:'#ff9a68'},
 {id:'laser',label:'LASER ALTIMETRY',color:'#76dfff'},
 {id:'fusion',label:'R&D SENSOR FUSION',color:'#c89bff'},
 {id:'magnetic',label:'MAGNETIC ANOMALY',color:'#f4d477'}
];
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function activeUnit(){return window.vigilGetActiveSimulationUnit&&window.vigilGetActiveSimulationUnit()||null;}
function unitIsDaedalus(){var u=activeUnit(),id=String(u&&u.id||'').toLowerCase();return id==='daedalus'||id==='daedalus-01';}
function regionalDaedalus(){return window.vigilGetRegionalSimulationUnit&&window.vigilGetRegionalSimulationUnit('daedalus')||null;}
function worldInfo(){return window.vigilGetCampaignWorld&&window.vigilGetCampaignWorld()||{id:'PELAGOS-01',name:'PELAGOS',seed:'PELAGOS-01'};}
function bus(){return window.CorelessRDLabBus||null;}
function busLatest(source){var b=bus();if(b&&typeof b.latest==='function')return b.latest(source);return null;}
function deterministicNoise(x,y,salt){var n=Math.sin((x+salt*.013)*127.1+(y-salt*.021)*311.7+salt*17.17)*43758.5453123;return (n-Math.floor(n))*2-1;}
function wrap(v){return ((v%1)+1)%1;}
function clamp(v,a,b){return Math.max(a,Math.min(b,v));}
function currentOrbitConfig(){
 var u=regionalDaedalus(),x=Number(u&&u.x),y=Number(u&&u.y);
 if(!Number.isFinite(x))x=.5;if(!Number.isFinite(y))y=.5;
 if(!orbitAnchor){
  orbitAnchor={x:wrap(x),y:clamp(y,0,1)};
  var lat=(.5-orbitAnchor.y)*Math.PI,ratio=clamp(Math.sin(lat)/Math.sin(INCLINATION),-1,1),phase0=Math.asin(ratio);
  orbitEpoch=Date.now()-(phase0/(Math.PI*2))*ORBIT_PERIOD_MS;
 }
 return {unit:u,anchor:orbitAnchor,altitudeKm:420,velocityKmS:7.66,periodMinutes:92.6,inclinationDeg:51.6};
}
function orbitPoint(time){
 var c=currentOrbitConfig(),elapsed=(Number(time)||Date.now())-orbitEpoch,phase=elapsed/ORBIT_PERIOD_MS*Math.PI*2+Math.asin(clamp(Math.sin((.5-c.anchor.y)*Math.PI)/Math.sin(INCLINATION),-1,1));
 var lat=Math.asin(clamp(Math.sin(INCLINATION)*Math.sin(phase),-1,1)),x=wrap(c.anchor.x+elapsed/ORBIT_PERIOD_MS),y=clamp(.5-lat/Math.PI,0,1);
 return {x:x,y:y,latitudeDeg:lat*180/Math.PI,longitudeDeg:(x-.5)*360,phase:phase};
}
function getRDFusion(){
 var r=busLatest('sensor-fusion'),d=r&&r.data||{},obs=Array.isArray(d.observations)?d.observations:[];
 function sigma(index,fallback){var n=Number(obs[index]&&obs[index].uncertainty_m);return Number.isFinite(n)&&n>0?n:fallback;}
 return {record:r,estimateM:Number(d.estimate_m),sigmaM:Number(d.uncertainty_1sigma_m),radarSigmaM:sigma(0,.6),opticalSigmaM:sigma(1,.2),laserSigmaM:sigma(2,1.1)};
}
function getRDState(){
 var optics=busLatest('optics'),specimen=busLatest('specimen'),materials=busLatest('materials'),fusion=getRDFusion(),eng=window.vigilDaedalusEngineeringAnalyses;
 if(!Array.isArray(eng)){try{eng=JSON.parse(localStorage.getItem('vigil-daedalus-engineering-analyses-v1')||'[]');}catch(e){eng=[];}}
 if(!Array.isArray(eng))eng=[];
 var b=bus(),records=b&&typeof b.snapshot==='function'?b.snapshot():[];
 return {optics:optics,specimen:specimen,materials:materials,fusion:fusion,engineering:eng.slice(-12).reverse(),records:records};
}
function surfaceElevation(terrain,x,y){
 if(!terrain)return 0;
 if(terrain.isLand)return 250+deterministicNoise(x,y,13)*900+deterministicNoise(x,y,31)*350;
 return -Math.max(0,Number(terrain.depthMeters)||0);
}
function weightedFusion(measurements){
 var weighted=0,total=0;
 measurements.forEach(function(m){var s=Math.max(.05,Number(m.sigma)||1),w=1/(s*s);weighted+=Number(m.value)*w;total+=w;});
 var sigma=total>0?Math.sqrt(1/total):Infinity;
 return {value:total>0?weighted/total:0,sigma:sigma};
}
function makeSample(x,y,row,col,rd){
 var terrain=window.vigilGetWorldTerrainAt?window.vigilGetWorldTerrainAt(x,y):null;
 if(!terrain)terrain={isLand:false,depthMeters:3000,temperatureC:2,magneticFieldNt:48000,riftCore:0,riftWall:0,biome:'SIMULATED OCEAN'};
 var truth=surfaceElevation(terrain,x,y),f=rd.fusion;
 var radarSigma=clamp(Number(f.radarSigmaM)||.6,.05,100),opticalSigma=clamp(Number(f.opticalSigmaM)||.2,.05,100),laserSigma=clamp(Number(f.laserSigmaM)||1.1,.05,100);
 var radar=truth+deterministicNoise(x,y,1+row*3+col)*radarSigma*1.7;
 var optical=truth+deterministicNoise(x,y,9+row*5+col)*opticalSigma*1.7;
 var laser=truth+deterministicNoise(x,y,23+row*7+col)*laserSigma*1.7;
 var fused=weightedFusion([{value:radar,sigma:radarSigma},{value:optical,sigma:opticalSigma},{value:laser,sigma:laserSigma}]);
 var optics=rd.optics&&rd.optics.data||{},detectorPower=Number(optics.detector_power_mw);
 if(!Number.isFinite(detectorPower)||detectorPower<=0)detectorPower=.95;
 var opticalGain=clamp(.45+Math.log10(1+detectorPower)*.38,.35,1.15);
 var reflectance=clamp((terrain.isLand?.56:.19)+(terrain.isLand?deterministicNoise(x,y,37)*.24:deterministicNoise(x,y,41)*.15)+opticalGain*.12,0,1);
 var thermalBase=terrain.isLand?13:3.2;
 var thermal=thermalBase+deterministicNoise(x,y,53)*4+(Number(terrain.riftCore)||0)*15+(Number(terrain.riftWall)||0)*2.5;
 var magnetic=Number(terrain.magneticFieldNt)||48000;
 var radarReturn=clamp(.16+(terrain.isLand?.36:.12)+reflectance*.23+(Number(terrain.riftWall)||0)*.28+Math.abs(deterministicNoise(x,y,61))*.12,0,1);
 var laserValid=terrain.isLand||!terrain.isLand&&Number(terrain.depthMeters)<10000;
 var opticalValid=reflectance>.25;
 var radial=clamp(1+fused.value/200000,.86,1.012);
 return {x:x,y:y,row:row,col:col,terrain:terrain,truthElevationM:truth,radarElevationM:radar,opticalElevationM:optical,laserElevationM:laser,fusedElevationM:fused.value,fusedSigmaM:fused.sigma,
  reflectance:reflectance,opticalGain:opticalGain,thermalC:thermal,magneticNt:magnetic,radarReturn:radarReturn,laserValid:laserValid,opticalValid:opticalValid,radial:radial};
}
function buildSurface(){
 var rd=getRDState(),next=[],nextCells=[],c=worldInfo();
 COLS=36;ROWS=18;
 for(var row=0;row<ROWS;row++){
  for(var col=0;col<COLS;col++){
   var x=(col+.5)/COLS,y=(row+.5)/ROWS;
   next.push(makeSample(x,y,row,col,rd));
   var x0=col/COLS,x1=(col+1)/COLS,y0=row/ROWS,y1=(row+1)/ROWS;
   nextCells.push({sample:next[next.length-1],coords:[[x0,y0],[x1,y0],[x1,y1],[x0,y1]]});
  }
 }
 samples=next;cells=nextCells;
 modelStats={
  radar:samples.filter(function(s){return s.radarReturn>.55;}).length,
  optical:samples.filter(function(s){return s.opticalValid;}).length,
  thermal:samples.filter(function(s){return s.thermalC>8;}).length,
  laser:samples.filter(function(s){return s.laserValid;}).length,
  fused:samples.filter(function(s){return s.fusedSigmaM<1;}).length
 };
 return c;
}
function createStyle(){
 if(document.getElementById('vigil-daedalus-orbital-style'))return;
 var st=document.createElement('style');st.id='vigil-daedalus-orbital-style';
 st.textContent=`
 #${BUTTON_ID}{display:inline-flex!important;align-items:center;justify-content:center;margin:6px 0 6px 7px;padding:9px 12px;background:#102b25;color:#c5f7df;border:1px solid #67cfa2;font: bold 10px "Courier New",monospace;letter-spacing:.7px;cursor:pointer}
 #${BUTTON_ID}[hidden]{display:none!important}
 #${VIEW_ID}{position:fixed;inset:0;z-index:2147483200;display:none;flex-direction:column;overflow:hidden;background:#020907;color:#c9f5de;font:11px/1.45 "Courier New",monospace}
 #${VIEW_ID}.open{display:flex}
 #${VIEW_ID} *{box-sizing:border-box}
 #${VIEW_ID} .vdo-head{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px 14px;background:#061910;border-bottom:1px solid #397b58;flex-wrap:wrap}
 #${VIEW_ID} .vdo-title{color:#b8f7d3;font-size:13px;font-weight:bold;letter-spacing:1.2px}
 #${VIEW_ID} .vdo-head small{color:#7fb899;font-size:9px}
 #${VIEW_ID} button{background:#0a281c;color:#c8f5dc;border:1px solid #397b58;padding:7px 10px;font:10px "Courier New",monospace;cursor:pointer}
 #${VIEW_ID} button:hover{background:#12452e;border-color:#8ae4ae}
 #${VIEW_ID} button[aria-pressed="true"]{background:#165538;border-color:#8be5ad;color:#fff}
 #${VIEW_ID} .vdo-meta{display:flex;flex-wrap:wrap;gap:6px 18px;padding:7px 12px;background:#03110b;border-bottom:1px solid #1c4932;color:#8bc8a5;font-size:9px}
 #${VIEW_ID} .vdo-main{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:0;min-height:0;flex:1}
 #${VIEW_ID} .vdo-stage{position:relative;min-width:0;min-height:0;background:radial-gradient(ellipse at 48% 48%,#0a241a 0%,#020907 68%);display:flex;align-items:stretch}
 #${VIEW_ID} canvas{display:block;width:100%;height:100%;min-height:260px;touch-action:none;cursor:grab}
 #${VIEW_ID} canvas:active{cursor:grabbing}
 #${VIEW_ID} .vdo-aside{overflow:auto;min-width:0;background:#03110c;border-left:1px solid #24563d;padding:10px}
 #${VIEW_ID} .vdo-block{border:1px solid #1d5037;background:#020a06;padding:9px;margin-bottom:9px}
 #${VIEW_ID} .vdo-block h3{font-size:10px;letter-spacing:1px;color:#9de5bb;margin:0 0 7px;padding-bottom:5px;border-bottom:1px solid #24563d}
 #${VIEW_ID} .vdo-layers{display:flex;flex-wrap:wrap;gap:5px}
 #${VIEW_ID} .vdo-layers button{font-size:8px;padding:6px 7px;color:#8fbea1}
 #${VIEW_ID} .vdo-metric{display:flex;justify-content:space-between;gap:8px;padding:4px 0;border-bottom:1px dotted #1d4933;font-size:9px}
 #${VIEW_ID} .vdo-metric:last-child{border-bottom:0}
 #${VIEW_ID} .vdo-metric span{color:#80ae94}
 #${VIEW_ID} .vdo-metric b{color:#d5f9e3;text-align:right;font-weight:normal}
 #${VIEW_ID} .vdo-record{border-top:1px solid #193d2b;padding:7px 0;font-size:9px;line-height:1.5}
 #${VIEW_ID} .vdo-record strong{display:block;color:#b9f2d0;font-size:9px}
 #${VIEW_ID} .vdo-record small{display:block;color:#7fa88e;margin-top:2px}
 #${VIEW_ID} .vdo-foot{padding:7px 12px;border-top:1px solid #24563d;background:#020a06;color:#7faf93;font-size:9px}
 #${VIEW_ID} .vdo-toolbar{display:flex;flex-wrap:wrap;gap:6px;padding:7px 12px;background:#04140c;border-top:1px solid #204d35}
 #${VIEW_ID} .vdo-toolbar .vdo-spacer{flex:1}
 #${VIEW_ID} .vdo-legend{display:flex;flex-wrap:wrap;gap:8px 12px;color:#7fae94;font-size:8px;padding:5px 12px}
 #${VIEW_ID} .vdo-key{display:inline-flex;align-items:center;gap:5px}
 #${VIEW_ID} .vdo-swatch{width:8px;height:8px;border-radius:50%;display:inline-block}
 @media(max-width:760px){#${VIEW_ID} .vdo-main{grid-template-columns:1fr;grid-template-rows:minmax(300px,52vh) minmax(180px,1fr)}#${VIEW_ID} .vdo-aside{border-left:0;border-top:1px solid #24563d}#${VIEW_ID} canvas{min-height:300px}#${VIEW_ID} .vdo-meta{gap:5px 10px}}
 `;
 document.head.appendChild(st);
}
function addMetric(parent,label,value){
 var row=document.createElement('div');row.className='vdo-metric';
 var a=document.createElement('span'),b=document.createElement('b');a.textContent=label;b.textContent=String(value==null?'—':value);
 row.appendChild(a);row.appendChild(b);parent.appendChild(row);
}
function renderRAndD(){
 if(!view)return;
 var list=view.querySelector('#vdo-rd-records'),metrics=view.querySelector('#vdo-rd-metrics');
 if(!list||!metrics)return;
 list.replaceChildren();metrics.replaceChildren();
 var rd=getRDState(),fusion=rd.fusion,fd=fusion.record&&fusion.record.data||{},opt=rd.optics&&rd.optics.data||{},mat=rd.materials&&rd.materials.data||{},spec=rd.specimen&&rd.specimen.data||{};
 addMetric(metrics,'FUSED RANGE',Number.isFinite(Number(fd.estimate_m))?Number(fd.estimate_m).toFixed(3)+' m':'AWAITING R&D RUN');
 addMetric(metrics,'FUSED 1σ',Number.isFinite(Number(fd.uncertainty_1sigma_m))?Number(fd.uncertainty_1sigma_m).toFixed(3)+' m':'DEFAULT MODEL');
 addMetric(metrics,'OPTICAL DETECTOR',Number.isFinite(Number(opt.detector_power_mw))?Number(opt.detector_power_mw).toFixed(4)+' mW':'AWAITING OPTICS TEST');
 addMetric(metrics,'STRUCTURAL TEST',mat.name?mat.name+' // '+Number(mat.yield_utilization_percent||0).toFixed(2)+'%':'NO MATERIAL TEST');
 addMetric(metrics,'REMOTE PROBE',spec.name?spec.name+' // '+String(spec.scan_mode||'').toUpperCase():'NO SPECIMEN SCAN');
 var records=rd.engineering.slice(0,8);
 records.forEach(function(r){
  var article=document.createElement('div');article.className='vdo-record';
  var title=document.createElement('strong');title.textContent=String(r.title||r.workspace||'DAEDALUS ENGINEERING RUN').toUpperCase();
  var detail=document.createElement('small');detail.textContent=String(r.result&&r.result.status||'RESULT ARCHIVED')+' // '+String(r.timestamp||'');
  article.appendChild(title);article.appendChild(detail);
  (r.result&&Array.isArray(r.result.rows)?r.result.rows.slice(0,3):[]).forEach(function(row){var p=document.createElement('small');p.textContent=String(row[0])+': '+String(row[1]);article.appendChild(p);});
  list.appendChild(article);
 });
 if(!records.length){var p=document.createElement('p');p.textContent='Engineering solvers are ready. Run an analysis in the Daedalus R&D tab to send its result into this VIGIL data view.';p.style.color='#80ae94';list.appendChild(p);}
}
function recordFeed(frame){
 if(typeof window.vigilRecordUnitSensorFeed!=='function')return {ok:false,reason:'VIGIL INPUT PIPELINE NOT READY'};
 return window.vigilRecordUnitSensorFeed(frame);
}
function toMeasurementRows(data){
 var rows=[];Object.keys(data||{}).forEach(function(k){
  var value=data[k];if(value===null||value===undefined||typeof value==='object')return;
  rows.push({label:k.replace(/_/g,' ').toUpperCase(),value:value,units:''});
 });
 return rows;
}
function bridgeRDRecord(record){
 if(!record||typeof record.source!=='string')return;
 var map={
  optics:{name:'R&D OPTICAL BENCH',modality:'optical',station:'DAEDALUS-RD-OPTICS'},
  specimen:{name:'REMOTE-PROBE SPECIMEN ANALYSIS',modality:'specimen_analysis',station:'DAEDALUS-RD-SPECIMEN'},
  materials:{name:'SPACECRAFT MATERIALS QUALIFICATION',modality:'materials',station:'DAEDALUS-RD-MATERIALS'},
  'sensor-fusion':{name:'R&D ORBITAL SENSOR FUSION',modality:'sensor_fusion',station:'DAEDALUS-RD-FUSION'}
 };
 var key=record.source,meta=map[key];
 if(!meta&&key.indexOf('engineering-')===0){
  var engineeringKey=key.slice('engineering-'.length),analysis=record.data||{};
  meta={name:'DAEDALUS '+engineeringKey.toUpperCase()+' ANALYSIS',modality:engineeringKey==='spatial'?'spatial_analysis':'engineering_analysis',station:'DAEDALUS-RD-'+engineeringKey.toUpperCase()};
  record={source:key,timestamp:record.timestamp,data:analysis};
 }
 if(!meta)return;
 var data=record.data||{};
 var rows=toMeasurementRows(data);
 if(data.result&&Array.isArray(data.result.rows))data.result.rows.forEach(function(r){rows.push({label:String(r[0]),value:String(r[1]),units:''});});
 recordFeed({unit_id:UNIT,sensor_id:meta.station,sensor_name:meta.name,modality:meta.modality,measurements:rows,detected_contacts:[],timestamp:record.timestamp});
}
function receiveEngineeringRecord(record){
 if(!record)return;
 var queue=window.vigilDaedalusEngineeringAnalyses;
 if(!Array.isArray(queue)){try{queue=JSON.parse(localStorage.getItem('vigil-daedalus-engineering-analyses-v1')||'[]');}catch(e){queue=[];}}
 if(!Array.isArray(queue))queue=[];
 var key=String(record.id||[record.timestamp,record.workspace,record.title].join('|'));
 if(!queue.some(function(item){return String(item&& (item.id||[item.timestamp,item.workspace,item.title].join('|')) )===key;})){queue.push(record);if(queue.length>60)queue.splice(0,queue.length-60);}
 window.vigilDaedalusEngineeringAnalyses=queue;
 try{localStorage.setItem('vigil-daedalus-engineering-analyses-v1',JSON.stringify(queue));}catch(e){}
 if(window.dispatchEvent)window.dispatchEvent(new CustomEvent('vigil:daedalus-engineering-analysis-archived',{detail:record}));
 renderRAndD();
}
function publishGlobalFeeds(force){
 var now=Date.now();if(!force&&now-lastFeedAt<15000)return;lastFeedAt=now;
 if(!samples.length)buildSurface();
 var own=regionalDaedalus();if(!own||typeof window.vigilGetPlanetRangeBearing!=='function')return;
 function hits(predicate,step,limit,prefix){
  var out=[];
  for(var i=0;i<samples.length;i++){
   var s=samples[i];if(i%step!==0||!predicate(s))continue;
   var g=window.vigilGetPlanetRangeBearing(Number(own.x),Number(own.y),s.x,s.y);
   if(!g||!Number.isFinite(g.bearing_deg)||!Number.isFinite(g.distance))continue;
   out.push({contact_id:prefix+'-'+String(s.row).padStart(2,'0')+'-'+String(s.col).padStart(2,'0'),classification:s.terrain.biome||'GLOBAL SURFACE RETURN',bearing_deg:g.bearing_deg,range_map_units:g.distance,confidence:clamp(.55+(s.radarReturn*.4),.2,.99)});
   if(out.length>=limit)continue;
  }
  return out;
 }
 var cfg=currentOrbitConfig(),point=orbitPoint(now),radarHits=hits(function(s){return s.radarReturn>.45;},7,120,'PEL-SAR'),
  opticalHits=hits(function(s){return s.opticalValid&&s.reflectance>.5;},11,90,'PEL-EO'),
  thermalHits=hits(function(s){return s.thermalC>6;},9,100,'PEL-IR'),
  laserHits=hits(function(s){return s.laserValid;},13,90,'PEL-LASER'),
  fusedHits=hits(function(s){return s.fusedSigmaM<1.5;},17,90,'PEL-FUSED');
 var frames=[
  {sensor_id:'DAEDALUS-01-ORBITAL-RADAR-GLOBAL',sensor_name:'ORBITAL RADAR // GLOBAL SURFACE RETURNS',modality:'radar',detected_contacts:radarHits,measurements:[{label:'ORBIT ALTITUDE',value:cfg.altitudeKm,units:'km'},{label:'GLOBAL SAMPLE CELLS',value:samples.length,units:'cells'},{label:'RADAR RETURNS',value:radarHits.length,units:'returns'},{label:'ORBITAL GROUND TRACK',value:point.latitudeDeg.toFixed(2)+'° / '+point.longitudeDeg.toFixed(2)+'°',units:''}]},
  {sensor_id:'DAEDALUS-01-OPTICAL-GLOBAL',sensor_name:'TELESCOPE / MULTISPECTRAL OPTICS // GLOBAL',modality:'optical',detected_contacts:opticalHits,measurements:[{label:'OPTICAL RETURNS',value:opticalHits.length,units:'features'},{label:'VISIBLE / NIR CALIBRATION',value:(busLatest('optics')&&busLatest('optics').data.wavelength_nm)||'532',units:'nm'},{label:'DETECTOR POWER',value:(busLatest('optics')&&busLatest('optics').data.detector_power_mw)||'SIM BASELINE',units:'mW'}]},
  {sensor_id:'DAEDALUS-01-THERMAL-GLOBAL',sensor_name:'MULTISPECTRAL IR ARRAY // GLOBAL',modality:'thermal',detected_contacts:thermalHits,measurements:[{label:'THERMAL ANOMALIES',value:thermalHits.length,units:'returns'},{label:'MODEL TEMPERATURE',value:'SURFACE IR / SYNTHETIC',units:''}]},
  {sensor_id:'DAEDALUS-01-LASER-ALT-GLOBAL',sensor_name:'LASER ALTIMETER // GLOBAL',modality:'lidar',detected_contacts:laserHits,measurements:[{label:'ALTIMETRY RETURNS',value:laserHits.length,units:'returns'},{label:'RANGE MODEL',value:'ORBITAL SLANT / SURFACE',units:''}]},
  {sensor_id:'DAEDALUS-01-RD-FUSION-GLOBAL',sensor_name:'R&D SENSOR FUSION // GLOBAL',modality:'sensor_fusion',detected_contacts:fusedHits,measurements:[{label:'FUSED RANGE ESTIMATE',value:getRDFusion().estimateM||0,units:'m'},{label:'FUSED 1σ UNCERTAINTY',value:getRDFusion().sigmaM||0,units:'m'},{label:'FUSED SURFACE CELLS',value:fusedHits.length,units:'cells'}]}
 ];
 frames.forEach(function(frame){frame.unit_id=UNIT;frame.timestamp=new Date(now).toISOString();recordFeed(frame);});
 window.vigilDaedalusOrbitalSensorModel={schema:'vigil.daedalus-orbital-sensor-model',version:1,unit_id:UNIT,world:worldInfo(),captured_at:new Date(now).toISOString(),orbit:point,global_cells:samples.length,frames:frames.map(function(f){return {sensor_id:f.sensor_id,modality:f.modality,returns:f.detected_contacts.length,measurements:f.measurements};})};
 if(view&&opened)renderReadouts();
}
function acceptRecord(record){
 bridgeRDRecord(record);
 if(record&&record.source&&record.source.indexOf('engineering-')===0)receiveEngineeringRecord(record.data||record);
 if(samples.length){buildSurface();publishGlobalFeeds(true);}
 if(opened){renderRAndD();draw();}
}
function buildView(){
 if(view)return;
 createStyle();view=document.createElement('section');view.id=VIEW_ID;view.setAttribute('role','dialog');view.setAttribute('aria-modal','true');view.setAttribute('aria-label','Daedalus global orbital 3D sensor display');
 view.innerHTML='<div class="vdo-head"><div><div class="vdo-title">DAEDALUS DE-01 // GLOBAL ORBITAL SENSOR ARRAY</div><small>VIGIL PLANETARY SURVEY // MULTI-INSTRUMENT 3D RECONSTRUCTION</small></div><button type="button" id="vdo-close">RETURN TO DAEDALUS SIMULATION</button></div>'+
 '<div class="vdo-meta"><span id="vdo-world">WORLD // PELAGOS-01</span><span id="vdo-orbit">ORBIT // 420 KM</span><span id="vdo-track">SUBPOINT // —</span><span id="vdo-coverage">GLOBAL MODEL // READY</span><span id="vdo-data-state">SYNTHETIC SIMULATION INPUTS</span></div>'+
 '<div class="vdo-main"><div class="vdo-stage"><canvas id="vdo-globe" aria-label="Rotatable 3D globe showing simulated orbital radar, optical, infrared, laser altimetry and fused sensor returns"></canvas></div><aside class="vdo-aside">'+
 '<section class="vdo-block"><h3>ACTIVE ORBITAL INSTRUMENT LAYERS</h3><div class="vdo-layers" id="vdo-layers"></div></section>'+
 '<section class="vdo-block"><h3>GLOBAL SENSOR RETURN COUNTS</h3><div id="vdo-counts"></div></section>'+
 '<section class="vdo-block"><h3>R&amp;D SOFTWARE // LIVE INPUTS TO VIGIL</h3><div id="vdo-rd-metrics"></div></section>'+
 '<section class="vdo-block"><h3>DAEDALUS ENGINEERING ANALYSIS ARCHIVE</h3><div id="vdo-rd-records"></div></section>'+
 '<section class="vdo-block"><h3>DISPLAY SOURCE / MODEL LIMITS</h3><p style="margin:0;color:#82ac94;font-size:9px;line-height:1.55">Pelagos-01 terrain is the deterministic campaign world model. Orbital radar, telescope, IR, laser-altimeter and fused returns are synthetic training observations generated from the mothership orbit and that world model. R&amp;D calibration and uncertainty settings alter the derived outputs. No live spacecraft, Earth geography or physical sensor connection is implied.</p></section>'+
 '</aside></div>'+
 '<div class="vdo-toolbar"><button type="button" id="vdo-rebuild">REGENERATE GLOBAL PASS</button><button type="button" id="vdo-zoom-out">ZOOM −</button><button type="button" id="vdo-zoom-in">ZOOM +</button><button type="button" id="vdo-reset">RESET VIEW</button><span class="vdo-spacer"></span><span style="color:#7eab92;font-size:9px">DRAG TO ROTATE // GLOBAL ORBITAL PERSPECTIVE</span></div>'+
 '<div class="vdo-legend" id="vdo-legend"></div><div class="vdo-foot" id="vdo-status">SIMULATION STANDBY // AWAITING DAEDALUS SENSOR PASS</div>';
 document.body.appendChild(view);canvas=view.querySelector('#vdo-globe');ctx=canvas.getContext('2d');
 var layerHost=view.querySelector('#vdo-layers');
 LAYERS.forEach(function(layer){
  var b=document.createElement('button');b.type='button';b.textContent=layer.label;b.dataset.layer=layer.id;b.setAttribute('aria-pressed',String(!!layerState[layer.id]));
  b.addEventListener('click',function(){layerState[layer.id]=!layerState[layer.id];b.setAttribute('aria-pressed',String(layerState[layer.id]));draw();});
  layerHost.appendChild(b);
 });
 var legend=view.querySelector('#vdo-legend');
 LAYERS.forEach(function(layer){var key=document.createElement('span');key.className='vdo-key';var sw=document.createElement('i');sw.className='vdo-swatch';sw.style.background=layer.color;var label=document.createElement('span');label.textContent=layer.label;key.appendChild(sw);key.appendChild(label);legend.appendChild(key);});
 view.querySelector('#vdo-close').addEventListener('click',close);
 view.querySelector('#vdo-rebuild').addEventListener('click',function(){buildSurface();publishGlobalFeeds(true);draw();status('GLOBAL ORBITAL PASS REGENERATED // '+samples.length+' SURFACE CELLS');});
 view.querySelector('#vdo-zoom-in').addEventListener('click',function(){zoom=clamp(zoom*1.12,0.65,1.8);draw();});
 view.querySelector('#vdo-zoom-out').addEventListener('click',function(){zoom=clamp(zoom/1.12,.65,1.8);draw();});
 view.querySelector('#vdo-reset').addEventListener('click',function(){yaw=0;pitch=0;zoom=1;draw();});
 canvas.addEventListener('pointerdown',function(e){drag={x:e.clientX,y:e.clientY,yaw:yaw,pitch:pitch};canvas.setPointerCapture(e.pointerId);});
 canvas.addEventListener('pointermove',function(e){if(!drag)return;yaw=drag.yaw+(e.clientX-drag.x)/Math.max(1,canvas.clientWidth)*2.6;pitch=clamp(drag.pitch+(e.clientY-drag.y)/Math.max(1,canvas.clientHeight)*2.1,-1.1,1.1);draw();});
 canvas.addEventListener('pointerup',function(){drag=null;});canvas.addEventListener('pointercancel',function(){drag=null;});
 canvas.addEventListener('wheel',function(e){e.preventDefault();zoom=clamp(zoom*(e.deltaY<0?1.08:.92),.65,1.8);draw();},{passive:false});
 view.addEventListener('click',function(e){if(e.target===view)close();});
 document.addEventListener('keydown',function(e){if(opened&&e.key==='Escape')close();});
 window.addEventListener('resize',resize);
}
function status(message){var n=view&&view.querySelector('#vdo-status');if(n)n.textContent=String(message||'');}
function resize(){
 if(!view||!canvas)return;var rect=canvas.getBoundingClientRect(),dpr=Math.min(window.devicePixelRatio||1,2);
 if(rect.width<2||rect.height<2)return;
 var w=Math.round(rect.width*dpr),h=Math.round(rect.height*dpr);
 if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;}
 draw();
}
function viewPoint(x,y,relief,orbit,cx,cy,r){
 var lat=(.5-y)*Math.PI,lon=(x-.5)*Math.PI*2,rr=r*(relief||1);
 var vx=Math.cos(lat)*Math.sin(lon)*rr,vy=Math.sin(lat)*rr,vz=Math.cos(lat)*Math.cos(lon)*rr;
 var lon0=(orbit.x-.5)*Math.PI*2,lat0=(.5-orbit.y)*Math.PI,theta=-lon0+yaw,ct=Math.cos(theta),st=Math.sin(theta);
 var x1=vx*ct+vz*st,z1=-vx*st+vz*ct,phi=lat0+pitch,cp=Math.cos(phi),sp=Math.sin(phi);
 var y2=vy*cp-z1*sp,z2=vy*sp+z1*cp;
 return {x:cx+x1,y:cy-y2,z:z2};
}
function colorForDepth(elev,terrain){
 if(terrain&&terrain.isLand)return elev>1000?'#c7b989':'#8aab79';
 var d=Math.max(0,-elev);
 if(d>12000)return '#081a2a';if(d>8000)return '#0a2940';if(d>5000)return '#0c3b53';if(d>2500)return '#0d5260';if(d>500)return '#137565';return '#246f57';
}
function tint(base,overlay,alpha){return base;}
function renderGlobe(){
 if(!ctx||!canvas||!view||!opened||!samples.length)return;
 var rect=canvas.getBoundingClientRect(),w=rect.width,h=rect.height;if(w<10||h<10)return;
 var dpr=Math.min(window.devicePixelRatio||1,2);ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);
 var orbit=orbitPoint(Date.now()),cfg=currentOrbitConfig(),cx=w*.48,cy=h*.5,R=Math.min(w*.43,h*.88)*zoom;
 var glow=ctx.createRadialGradient(cx,cy,R*.68,cx,cy,R*1.25);glow.addColorStop(0,'rgba(18,75,48,.18)');glow.addColorStop(1,'rgba(2,9,7,0)');ctx.fillStyle=glow;ctx.fillRect(0,0,w,h);
 var projected=[];
 cells.forEach(function(cell){
  var p=cell.coords.map(function(c){return viewPoint(c[0],c[1],cell.sample.radial,orbit,cx,cy,R);});
  var center=viewPoint(cell.sample.x,cell.sample.y,cell.sample.radial,orbit,cx,cy,R);
  if(center.z<=-.01)return;
  projected.push({cell:cell,points:p,center:center});
 });
 projected.sort(function(a,b){return a.center.z-b.center.z;});
 projected.forEach(function(item){
  var s=item.cell.sample,p=item.points;
  ctx.beginPath();ctx.moveTo(p[0].x,p[0].y);for(var i=1;i<p.length;i++)ctx.lineTo(p[i].x,p[i].y);ctx.closePath();
  ctx.fillStyle=colorForDepth(s.fusedElevationM,s.terrain);ctx.fill();
  if(layerState.fusion){ctx.fillStyle=s.fusedSigmaM<.4?'rgba(195,155,255,.16)':'rgba(195,155,255,.06)';ctx.fill();}
  if(layerState.radar){ctx.fillStyle='rgba(90,255,175,'+(0.04+s.radarReturn*.13)+')';ctx.fill();}
  if(layerState.optical&&s.opticalValid){ctx.fillStyle='rgba(220,255,233,'+(0.025+s.reflectance*.08)+')';ctx.fill();}
  if(layerState.thermal){var heat=clamp((s.thermalC+2)/24,0,1);ctx.fillStyle='rgba(255,'+Math.round(175-heat*105)+',75,'+(heat*.13)+')';ctx.fill();}
  if(layerState.laser&&s.laserValid){ctx.strokeStyle='rgba(91,218,255,.25)';ctx.lineWidth=.55;ctx.stroke();}
  if(layerState.magnetic&&Math.abs(s.magneticNt-25)>25){ctx.fillStyle='rgba(250,214,115,.18)';ctx.fill();}
  ctx.strokeStyle='rgba(95,174,128,.19)';ctx.lineWidth=.45;ctx.stroke();
 });
 // Global latitude/longitude frame, clipped by the visible hemisphere.
 ctx.save();ctx.strokeStyle='rgba(151,224,181,.22)';ctx.lineWidth=.7;
 for(var latIndex=-60;latIndex<=60;latIndex+=30){
  ctx.beginPath();var started=false;
  for(var lonIndex=0;lonIndex<=360;lonIndex+=5){var p=viewPoint(lonIndex/360, .5-latIndex/180,1,orbit,cx,cy,R);if(p.z>0){if(!started){ctx.moveTo(p.x,p.y);started=true;}else ctx.lineTo(p.x,p.y);}else started=false;}
  ctx.stroke();
 }
 for(var lonLine=0;lonLine<360;lonLine+=30){
  ctx.beginPath();var begun=false;
  for(var latLine=-90;latLine<=90;latLine+=3){var p=viewPoint(lonLine/360,.5-latLine/180,1,orbit,cx,cy,R);if(p.z>0){if(!begun){ctx.moveTo(p.x,p.y);begun=true;}else ctx.lineTo(p.x,p.y);}else begun=false;}
  ctx.stroke();
 }
 ctx.restore();
 // Project the mothership ground track for the previous and next orbit segment.
 ctx.save();ctx.strokeStyle='rgba(112,255,190,.86)';ctx.lineWidth=1.6;ctx.setLineDash([5,4]);ctx.beginPath();var trackStarted=false;
 for(var dt=-2400;dt<=2400;dt+=90){var op=orbitPoint(Date.now()+dt*1000),tp=viewPoint(op.x,op.y,1.001,orbit,cx,cy,R);if(tp.z>0){if(!trackStarted){ctx.moveTo(tp.x,tp.y);trackStarted=true;}else ctx.lineTo(tp.x,tp.y);}else trackStarted=false;}
 ctx.stroke();ctx.setLineDash([]);
 var sub=viewPoint(orbit.x,orbit.y,1.006,orbit,cx,cy,R);
 if(sub.z>0){
  ctx.strokeStyle='#b7ffe0';ctx.fillStyle='rgba(45,255,157,.12)';ctx.lineWidth=1.5;ctx.beginPath();ctx.ellipse(sub.x,sub.y,R*.075,R*.027,-.24,0,Math.PI*2);ctx.fill();ctx.stroke();
  ctx.beginPath();ctx.arc(sub.x,sub.y,4,0,Math.PI*2);ctx.fillStyle='#ecfff4';ctx.fill();ctx.strokeStyle='#41e892';ctx.stroke();
  ctx.fillStyle='#baffd9';ctx.font='9px Courier New';ctx.fillText('DE-01 SUBPOINT',sub.x+8,sub.y-8);
 }
 ctx.restore();
 // Global sensor detections, each tied to a separate synthetic instrument modality.
 ctx.save();
 projected.forEach(function(item){
  var s=item.cell.sample,p=item.center;
  if(p.z<.08)return;
  if(layerState.radar&&s.radarReturn>.62){ctx.strokeStyle='#72ffbb';ctx.lineWidth=1;ctx.strokeRect(p.x-2.4,p.y-2.4,4.8,4.8);}
  if(layerState.optical&&s.opticalValid&&s.reflectance>.64){ctx.fillStyle='#d8ffe5';ctx.beginPath();ctx.arc(p.x,p.y,1.5,0,Math.PI*2);ctx.fill();}
  if(layerState.thermal&&s.thermalC>8){ctx.strokeStyle='#ff9a68';ctx.lineWidth=1.1;ctx.beginPath();ctx.arc(p.x,p.y,2.5,0,Math.PI*2);ctx.stroke();}
  if(layerState.laser&&s.laserValid&&((s.row+s.col)%4===0)){ctx.strokeStyle='#76dfff';ctx.beginPath();ctx.moveTo(p.x-3,p.y);ctx.lineTo(p.x+3,p.y);ctx.moveTo(p.x,p.y-3);ctx.lineTo(p.x,p.y+3);ctx.stroke();}
  if(layerState.fusion&&s.fusedSigmaM<.45&&((s.row+s.col)%5===0)){ctx.fillStyle='#c89bff';ctx.fillRect(p.x-1,p.y-1,2,2);}
 });
 ctx.restore();
 // Fleet craft positions from the active VIGIL simulation.
 var fleet=window.vigilGetRegionalSensorContacts?window.vigilGetRegionalSensorContacts():[];
 fleet.filter(function(u){return u&&u.id!==UNIT&&u.deployment_status==='deployed';}).forEach(function(u){
  var p=viewPoint(u.x,u.y,1.008,orbit,cx,cy,R);if(p.z<=0)return;
  ctx.fillStyle=u.side==='friendly'?'#85ffbd':'#ffd27c';ctx.strokeStyle='#03100a';ctx.lineWidth=1;ctx.fillRect(p.x-3,p.y-3,6,6);ctx.strokeRect(p.x-3,p.y-3,6,6);
 });
 // Atmospheric rim and globe outline.
 ctx.save();ctx.beginPath();ctx.arc(cx,cy,R,0,Math.PI*2);ctx.strokeStyle='rgba(113,255,187,.45)';ctx.lineWidth=2;ctx.stroke();ctx.restore();
 ctx.fillStyle='#a9e9c1';ctx.font='10px Courier New';ctx.fillText('PELAGOS-01 // GLOBAL SURFACE MODEL',12,18);
 ctx.fillStyle='#75b994';ctx.font='9px Courier New';ctx.fillText('SYNTHETIC ORBITAL RETURNS // '+samples.length+' GRID CELLS',12,32);
}
function renderReadouts(){
 if(!view)return;
 var counts=view.querySelector('#vdo-counts');counts.replaceChildren();
 addMetric(counts,'GLOBAL MODEL CELLS',samples.length);
 addMetric(counts,'RADAR BACKSCATTER RETURNS',modelStats.radar);
 addMetric(counts,'OPTICAL FEATURES',modelStats.optical);
 addMetric(counts,'IR ANOMALIES',modelStats.thermal);
 addMetric(counts,'LASER ALTIMETRY CELLS',modelStats.laser);
 addMetric(counts,'FUSED CELLS',modelStats.fused);
 var cfg=currentOrbitConfig(),p=orbitPoint(Date.now()),world=worldInfo(),fusion=getRDFusion();
 view.querySelector('#vdo-world').textContent='WORLD // '+String(world.id||'PELAGOS-01');
 view.querySelector('#vdo-orbit').textContent='ORBIT // '+cfg.altitudeKm+' KM // '+cfg.velocityKmS+' KM/S // '+cfg.periodMinutes+' MIN';
 view.querySelector('#vdo-track').textContent='SUBPOINT // '+p.latitudeDeg.toFixed(1)+'° LAT / '+p.longitudeDeg.toFixed(1)+'° LON';
 view.querySelector('#vdo-coverage').textContent='GLOBAL MODEL // '+samples.length+' CELLS / '+Math.round((modelStats.fused/Math.max(1,samples.length))*100)+'% FUSED';
 view.querySelector('#vdo-data-state').textContent='SIMULATION INPUTS // R&D '+(fusion.record?'CONNECTED':'BASELINE');
 renderRAndD();
}
function draw(){if(!opened)return;renderGlobe();if(Date.now()-lastReadoutAt>1000){renderReadouts();lastReadoutAt=Date.now();}}
function open(){
 if(!unitIsDaedalus()){status('SELECT DAEDALUS DE-01 IN SIMULATION BAY TO OPEN THE ORBITAL ARRAY');return;}
 buildView();buildSurface();publishGlobalFeeds(true);opened=true;previousBodyOverflow=document.body.style.overflow;document.body.style.overflow='hidden';view.classList.add('open');resize();renderReadouts();status('ORBITAL SENSOR SUITE ONLINE // GLOBAL SYNTHETIC PASS ACTIVE');
 if(!raf)raf=requestAnimationFrame(loop);
}
function close(){if(!view)return;opened=false;view.classList.remove('open');document.body.style.overflow=previousBodyOverflow;if(raf){cancelAnimationFrame(raf);raf=0;}}
function loop(t){
 if(!opened){raf=0;return;}
 if(!lastDrawAt||t-lastDrawAt>120){draw();lastDrawAt=t;}
 publishGlobalFeeds(false);
 raf=requestAnimationFrame(loop);
}
function updateButton(){
 var display=document.getElementById('vigil-unit-sensor-display');if(!display)return false;
 var launch=display.querySelector('#'+BUTTON_ID);
 if(!launch){launch=document.createElement('button');launch.type='button';launch.id=BUTTON_ID;launch.textContent='OPEN ORBITAL GLOBAL 3D SENSOR VIEW';launch.title='Open Daedalus global 3D orbital sensor visualization';launch.addEventListener('click',open);
  var anchor=display.querySelector('#vigil-3d-seafloor-launch');if(anchor&&anchor.parentNode)anchor.parentNode.insertBefore(launch,anchor.nextSibling);else display.insertBefore(launch,display.firstChild);
 }
 button=launch;launch.hidden=!unitIsDaedalus();
 return true;
}
function boot(){
 updateButton();
 window.addEventListener('vigil:active-unit-changed',function(){updateButton();});
 window.addEventListener('vigil:simulation-unit-state-changed',function(){if(opened){publishGlobalFeeds(true);draw();}});
 window.addEventListener('coreless:rd-data',function(e){acceptRecord(e&&e.detail);});
 window.addEventListener('vigil:daedalus-engineering-analysis',function(e){receiveEngineeringRecord(e&&e.detail);if(opened)draw();});
 if(window.vigilDaedalusEngineeringAnalyses&&Array.isArray(window.vigilDaedalusEngineeringAnalyses))window.vigilDaedalusEngineeringAnalyses.slice(-12).forEach(function(record){receiveEngineeringRecord(record);bridgeRDRecord({source:'engineering-'+String(record.workspace||'analysis'),timestamp:record.timestamp,data:record});});
 var b=bus();if(b&&typeof b.snapshot==='function')b.snapshot().forEach(bridgeRDRecord);
 window.setInterval(function(){if(!button||!document.body.contains(button))updateButton();else button.hidden=!unitIsDaedalus();},1000);
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();
