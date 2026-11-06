(function(){
'use strict';
var STORE='vigil-fleet-unit-sensor-reports-v1',MAX_REPORTS=180;
var sensorPackages={
 ship:{name:'DDG-51 // DESTROYER',sensors:[
  ['AIR / SURFACE SEARCH RADAR','radar','surface',.48],['HULL-MOUNTED SONAR','sonar','underwater',.16],
  ['EO FIRE-CONTROL DIRECTOR','optical','surface',.15],['IR SEARCH / TRACK','thermal','surface',.2],
  ['ESM / RADAR WARNING RECEIVER','esm','emitter',.2],['GNSS / INERTIAL NAVIGATION','imu','navigation',1],
  ['LASER RANGEFINDER','rangefinder','surface',.08],['COMBAT SYSTEM TRACK FUSION','tracking','fused',.5],
  ['WEAPON FIRE-CONTROL SOLUTION','fire_control','surface',.45],['SHIP TELEMETRY','telemetry','link',1]
 ]},
 daedalus:{name:'DAEDALUS DE-01 // ORBITAL MOTHERSHIP',sensors:[
  ['ORBITAL SEARCH RADAR','radar','orbital',.12],['STAR TRACKER / ATTITUDE REFERENCE','star_tracker','navigation',1],
  ['PELAGOS GLOBAL OBSERVATION TELESCOPE','optical','orbital',.12],['MULTISPECTRAL IR ARRAY','thermal','orbital',.12],
  ['LASER COMMUNICATIONS TERMINAL','lasercom','link',1],['ASTRODYNAMICS / INERTIAL NAVIGATION','imu','navigation',1],
  ['SPACE RADIATION MONITOR','radiation','environment',1],['DOCKING / PROXIMITY LIDAR','lidar','docking',.03],
  ['REACTOR / POWER DISTRIBUTION MONITOR','power','engineering',1],['STRUCTURAL / MATERIALS HEALTH MONITOR','materials','engineering',1],['REMOTE-PROBE SPECIMEN ANALYZER','specimen_analysis','science',.2],['HABITAT / LIFE-SUPPORT MONITOR','life_support','environment',1],
  ['DEEP-SPACE TELEMETRY / NETWORK','telemetry','link',1]
 ]},
 drone:{name:'DRONE-01 // UNCREWED AERIAL VEHICLE',sensors:[
  ['EO GIMBAL CAMERA','optical','surface',.12],['THERMAL IMAGER','thermal','surface',.13],
  ['LASER ALTIMETER / RANGEFINDER','rangefinder','terrain',.06],['SCANNING LIDAR','lidar','terrain',.05],
  ['GNSS / FLIGHT IMU','imu','navigation',1],['PROXIMITY / COLLISION SENSOR','proximity','obstacle',.02],
  ['AIR-DATA / PRESSURE PROBES','air_data','environment',1],['SECURE DATA-LINK TERMINAL','lasercom','link',1],
  ['ONBOARD OBJECT TRACKER','tracking','fused',.18]
 ]},
 submersible:{name:'UUV-01 // UNDERSEA SURVEY VEHICLE',sensors:[
  ['FORWARD-LOOKING IMAGING SONAR','sonar','underwater',.06],['MULTIBEAM ECHOSOUNDER','multibeam','bathymetry',.05],
  ['SIDE-SCAN SONAR','side_scan','bathymetry',.05],['DOPPLER VELOCITY LOG','dvl','navigation',1],
  ['DEPTH / PRESSURE TRANSDUCER','depth','environment',1],['CTD // CONDUCTIVITY / TEMPERATURE / DEPTH','ctd','environment',1],
  ['MARINE MAGNETOMETER','magnetometer','geology',.04],['LOW-LIGHT UNDERWATER CAMERA','underwater_camera','underwater',.025],
  ['PROXIMITY SONAR','proximity','obstacle',.015],['INERTIAL NAVIGATION UNIT','imu','navigation',1],
  ['ACOUSTIC TELEMETRY MODEM','telemetry','link',1]
 ]},
 submarine:{name:'SSN-774 // ATTACK SUBMARINE',sensors:[
  ['PASSIVE ACOUSTIC ARRAYS','passive_sonar','underwater',.25],['BOW-MOUNTED ACTIVE SONAR','sonar','underwater',.18],
  ['FLANK ARRAY SONAR','flank_sonar','underwater',.24],['TOWED ARRAY LISTENING SYSTEM','towed_array','underwater',.35],
  ['PERISCOPE / EO IMAGING','optical','surface',.1],['ESM / ELECTRONIC SUPPORT MAST','esm','emitter',.25],
  ['DEPTH / PRESSURE SENSOR','depth','environment',1],['DOPPLER LOG / INERTIAL NAVIGATION','dvl','navigation',1],
  ['TACTICAL TRACK FUSION','tracking','fused',.4],['WEAPON FIRE-CONTROL SYSTEM','fire_control','underwater',.3]
 ]},
 mech:{name:'MECH-01 // WALKING MANIPULATOR PLATFORM',sensors:[
  ['STEREO EO / HEAD-MOUNTED DISPLAY','optical','surface',.025],['THERMAL / IR CAMERA','thermal','surface',.025],
  ['360° SOLID-STATE LIDAR','lidar','obstacle',.035],['PROXIMITY / ULTRASONIC ARRAY','proximity','obstacle',.008],
  ['JOINT ABSOLUTE ENCODERS','encoders','actuator',1],['FORCE / TORQUE TRANSDUCERS','force_torque','actuator',1],
  ['INERTIAL MEASUREMENT UNIT','imu','navigation',1],['MOTOR / POWER ELECTRONICS MONITOR','power','engineering',1]
 ]},
 facility:{name:'FAC-01 // FIXED SENSOR INSTALLATION',sensors:[
  ['PERIMETER SURVEILLANCE RADAR','radar','surface',.12],['FIXED EO CAMERA NETWORK','fixed_camera','surface',.08],
  ['THERMAL PERIMETER ARRAY','thermal','surface',.08],['ACCESS / DOOR CONTACT NETWORK','access_alarm','security',.01],
  ['WEATHER / ENVIRONMENT STATION','environmental','environment',1],['ACOUSTIC / VIBRATION ARRAY','acoustic','acoustic',.04],
  ['RF / ESM MONITOR','esm','emitter',.15],['INSTALLATION NETWORK / TELEMETRY','telemetry','link',1]
 ]}
};
var sharedSources={
 'DAEDALUS-01':{name:'DAEDALUS DE-01 // ORBITAL MOTHERSHIP',kind:'ORBITAL MOTHERSHIP',coverage:.12,
  services:['Fleet data relay','Precision time reference','Orbital / inertial navigation corrections','Shared track archive','R&D experiment archive','Laser communications gateway']},
 'FAC-01':{name:'FAC-01 // FIXED SENSOR INSTALLATION',kind:'FIXED INSTALLATION',coverage:.02,
  services:['Local sensor fusion and track relay','Ground navigation / timing reference','Regional map and terrain cache','Environmental / weather reference','R&D archive and maintenance records','Secure RF communications gateway']}
};
function unitId(value){
 var v=String(value||'').toLowerCase(),aliases={ship:'DDG-51',daedalus:'DAEDALUS-01',drone:'DRONE-01',submersible:'UUV-01',submarine:'SSN-774',mech:'MECH-01',facility:'FAC-01'};
 return aliases[v]||String(value||'').toUpperCase();
}
function profileKey(id){
 var resolved=unitId(id);if(/^MECH-/.test(resolved))return 'mech';
 return {'DDG-51':'ship','DAEDALUS-01':'daedalus','DRONE-01':'drone','UUV-01':'submersible','SSN-774':'submarine','MECH-01':'mech','FAC-01':'facility'}[resolved]||'ship';
}
function sensorsForUnit(id){
 var pkg=sensorPackages[profileKey(id)];if(!pkg)return [];
 if(profileKey(id)!=='mech')return pkg.sensors;
 var u=null;try{u=window.vigilGetRegionalSimulationUnit&&window.vigilGetRegionalSimulationUnit(unitId(id));}catch(e){}
 var parts=u&&u.mech_parts||{},mounts=u&&u.mech_mounts||{},out=[];
 if(parts['MOBILITY BASE'])out.push(['JOINT ABSOLUTE ENCODERS','encoders','actuator',1],['FORCE / TORQUE TRANSDUCERS','force_torque','actuator',1]);
 if(parts['SYSTEM COM'])out.push(['INERTIAL MEASUREMENT UNIT','imu','navigation',1]);
 if(parts.GENERATOR)out.push(['MOTOR / POWER ELECTRONICS MONITOR','power','engineering',1]);
 Object.keys(mounts).forEach(function(slot){
  var id=String(mounts[slot]||'');
  if(id==='AS-THERM')out.push(['THERMAL / IR CAMERA','thermal','surface',.025]);
  if(id==='AS-NV')out.push(['STEREO EO / HEAD-MOUNTED DISPLAY','optical','surface',.025]);
  if(id==='AS-MINE')out.push(['MINE DETECTION / PROXIMITY ARRAY','proximity','obstacle',.008]);
 });
 return out;
}
function currentContacts(){try{return window.vigilGetRegionalSensorContacts?window.vigilGetRegionalSensorContacts():[];}catch(e){return [];}}
function getUnit(id){
 var resolved=unitId(id),key=profileKey(resolved);
 try{return window.vigilGetRegionalSimulationUnit?window.vigilGetRegionalSimulationUnit(/^MECH-/.test(resolved)?resolved:key):null;}catch(e){return null;}
}
function distance(a,b){
 if(!a||!b)return Infinity;
 if(window.vigilGetPlanetRangeBearing){var g=window.vigilGetPlanetRangeBearing(Number(a.x),Number(a.y),Number(b.x),Number(b.y));if(g&&Number.isFinite(Number(g.distance)))return Number(g.distance);}
 return Math.hypot(Number(a.x)-Number(b.x),Number(a.y)-Number(b.y));
}
function localSource(id){
 id=unitId(id);
 if(sharedSources[id])return {id:id,name:sharedSources[id].name,kind:sharedSources[id].kind,distance:0,linkQuality:1,coverage:sharedSources[id].coverage,services:sharedSources[id].services.slice(),local:true};
 var unit=getUnit(id);if(!unit)return null;
 var candidates=currentContacts().filter(function(c){return c&&c.side==='friendly'&&sharedSources[c.id];}).map(function(c){
  var p=sharedSources[c.id],d=distance(unit,c);return {id:c.id,name:p.name,kind:p.kind,distance:d,coverage:p.coverage,linkQuality:Math.max(0,Math.min(1,1-d/p.coverage)),services:p.services.slice(),local:d<=p.coverage};
 }).filter(function(x){return x.local;});
 candidates.sort(function(a,b){return a.distance-b.distance;});
 return candidates[0]||null;
}
function stableNoise(id,label){
 var x=2166136261,s=String(id)+'|'+String(label);for(var i=0;i<s.length;i++){x^=s.charCodeAt(i);x=Math.imul(x,16777619);}return (x>>>0)/4294967295;
}
function resolveSensor(id,station){
 var pkg={sensors:sensorsForUnit(id)},raw=String(station||'').toLowerCase();
 var match=pkg.sensors.find(function(s){return s[0].toLowerCase()===raw||s[0].toLowerCase().indexOf(raw)>=0||raw.indexOf(s[0].toLowerCase())>=0;});
 if(match)return match;
 var aliasMap=[
  [/sonar|acoustic/,['sonar','passive_sonar','flank_sonar','towed_array','side_scan','multibeam','proximity']],
  [/seafloor|bathymetry|mapping/,['multibeam','side_scan']],
  [/eo camera|camera|optical|periscope/,['optical','fixed_camera','underwater_camera']],
  [/thermal|infrared|ir/,['thermal']],
  [/radar/,['radar']],
  [/esm|rf/,['esm']],
  [/navigation|inertial|imu|dvl/,['imu','dvl']],
  [/rangefinder|range|lidar/,['rangefinder','lidar']],
  [/tracking|fused|fire control/,['tracking','fire_control']],
  [/laser communication|lasercom/,['lasercom']],
  [/star tracker/,['star_tracker']],
  [/radiation/,['radiation']],
  [/power|reactor/,['power']],
  [/life support/,['life_support']],
  [/telemetry/,['telemetry']],
  [/depth/,['depth']],
  [/ctd/,['ctd']],
  [/magnetometer/,['magnetometer']],
  [/proximity/,['proximity']],
  [/encoder/,['encoders']],
  [/force|torque/,['force_torque']],
  [/environment|weather/,['environmental']],
  [/access|alarm/,['access_alarm']]
 ];
 for(var i=0;i<aliasMap.length;i++)if(aliasMap[i][0].test(raw)){var found=pkg.sensors.find(function(s){return aliasMap[i][1].indexOf(s[1])>=0;});if(found)return found;}
 return null;
}
function detections(id,sensor){
 var own=getUnit(id);if(!own)return [];
 var pkg=sensor[2],range=sensor[3],h=Number(own.heading_deg)||0;
 return currentContacts().filter(function(c){
  if(!c||c.side!=='contact'||!Number.isFinite(Number(c.x))||!Number.isFinite(Number(c.y)))return false;
  var d=distance(own,c);if(d>range)return false;
  if(pkg==='emitter'&&['carrier','destroyer','mothership'].indexOf(String(c.ship_class||''))<0)return false;
  if(pkg==='surface'||pkg==='orbital'||pkg==='underwater'){
   var bearing=(Math.atan2(Number(c.x)-Number(own.x),-(Number(c.y)-Number(own.y)))*180/Math.PI+360)%360;
   var fov=sensor[1]==='thermal'?100: sensor[1]==='optical'?60:180,delta=Math.abs(((bearing-h+540)%360)-180);if(delta>fov/2)return false;
  }
  return true;
 }).map(function(c){
  var d=distance(own,c),bearing=(Math.atan2(Number(c.x)-Number(own.x),-(Number(c.y)-Number(own.y)))*180/Math.PI+360)%360;
  return {contact_id:c.id,range_map_units:Number(d.toFixed(4)),bearing_deg:Number(bearing.toFixed(1)),classification:c.label||c.id,
   confidence:Number(Math.max(.2,Math.min(.98,1-d/Math.max(.001,range))).toFixed(3)),source_unit_id:own.id};
 });
}
function measurementRows(id,sensor,unit,source,hits){
 var modality=sensor[1],noise=stableNoise(id,sensor[0]),h=Number(unit.heading_deg)||0,speed=Number(unit.speed)||0,depth=Number(unit.depth_meters)||0;
 var nearest=hits.slice().sort(function(a,b){return a.range_map_units-b.range_map_units;})[0],rows=[];
 function add(label,value,units){rows.push({label:label,value:value,units:units||''});}
 add('CHANNEL',sensor[0],'');
 // Qualified R&D results are applied only to Daedalus DE-01.
 var daedalusRD=profileKey(id)==='daedalus'&&window.vigilDaedalusRDIntegration?window.vigilDaedalusRDIntegration.getQualifiedModules():null;
 if(daedalusRD){
  if(modality==='optical'&&daedalusRD.optics){add('R&D QUALIFICATION','OPTICAL BENCH / QUALIFIED','');add('CALIBRATED WAVELENGTH',daedalusRD.optics.data.wavelength_nm||'—','nm');add('DETECTOR POWER',Number(daedalusRD.optics.data.detector_power_mw||0).toFixed(4),'mW');}
  if((modality==='radar'||modality==='star_tracker'||modality==='imu')&&daedalusRD['sensor-fusion']){add('R&D FUSION','ORBITAL ESTIMATOR QUALIFIED','');add('FUSED RANGE',Number(daedalusRD['sensor-fusion'].data.estimate_m||0).toFixed(3),'m');add('FUSED 1σ',Number(daedalusRD['sensor-fusion'].data.uncertainty_1sigma_m||0).toFixed(3),'m');}
  if(modality==='power'&&daedalusRD.materials){add('STRUCTURES TEST','MATERIAL MODEL QUALIFIED','');add('TEST MATERIAL',daedalusRD.materials.data.name||'—','');add('YIELD UTILIZATION',Number(daedalusRD.materials.data.yield_utilization_percent||0).toFixed(2),'%');}
 }
 if(modality==='radar'){
  add('FREQUENCY BAND',profileKey(id)==='daedalus'?'X-BAND / SPACE':'S-BAND / X-BAND','');
  add('SCAN RATE',(6+noise*2).toFixed(1),'rpm');add('RANGE RESOLUTION',profileKey(id)==='daedalus'?'1.5':'150','m');if(profileKey(id)==='daedalus'){add('ORBITAL SWATH','GLOBAL / MULTI-PASS','');add('OBSERVATION FRAME','PELAGOS PLANET-CENTERED','');}add('TRACK RETURNS',hits.length,'contacts');
  add('PRIMARY RETURN',nearest?nearest.contact_id:'NO RETURN','');if(nearest)add('RANGE / BEARING',nearest.range_map_units.toFixed(3)+' / '+nearest.bearing_deg.toFixed(1),'map units / deg');
 }else if(['sonar','passive_sonar','flank_sonar','towed_array','multibeam','side_scan','acoustic','proximity'].indexOf(modality)>=0){
  add('SOUND SPEED ESTIMATE',(1480+noise*18-depth*.0003).toFixed(1),'m/s');add('SELF-NOISE INDEX',(54+speed*380+noise*3).toFixed(1),'dB model');add('DETECTED RETURNS',hits.length,'contacts');
  add('BOTTOM / ECHO CONFIDENCE',Math.max(.2,.97-depth/18000).toFixed(2),'0–1');if(nearest)add('NEAREST BEARING',nearest.bearing_deg.toFixed(1),'deg');
  if(modality==='multibeam')add('SWATH WIDTH',(120+noise*35).toFixed(1),'deg');if(modality==='side_scan')add('BACKSCATTER INDEX',(0.2+noise*.7).toFixed(3),'normalized');
 }else if(modality==='optical'||modality==='fixed_camera'||modality==='underwater_camera'){
  add('FIELD OF VIEW',modality==='underwater_camera'?'72 × 48':'42 × 28','deg');add('IMAGE FORMAT',modality==='optical'?'4096 × 2160':'1920 × 1080','pixels');
  add('OBJECT RETURNS',hits.length,'tracks');add('BORESIGHT',h.toFixed(1),'deg');add('IMAGE QUALITY',Math.max(.25,.96-noise*.12).toFixed(2),'normalized');
 }else if(modality==='thermal'){
  if(profileKey(id)==='daedalus'){
   var orbitalTemp=Number((210+noise*72).toFixed(1));
   add('INSTRUMENT','ORBITAL MULTISPECTRAL IR RADIOMETER','');
   add('BRIGHTNESS TEMPERATURE',orbitalTemp,'K');
   add('SPECTRAL CHANNELS','MWIR / LWIR','');
   add('GROUND SAMPLE DISTANCE','SIMULATED ORBITAL PIXEL','');
   add('RADIOMETRIC CONTRAST',(2+noise*8).toFixed(2),'K');
   add('NETD',.04,'K');add('SURFACE RETURNS',hits.length,'pixels / tracks');
  }else{
   add('SCENE TEMPERATURE',(18+noise*9-depth/5000).toFixed(1),'°C');add('THERMAL CONTRAST',(4+noise*11).toFixed(1),'K');
   add('NETD',.04,'K');add('HEAT RETURNS',hits.length,'tracks');
  }
 }else if(modality==='esm'){
  add('FREQUENCY COVERAGE','0.5–18','GHz');add('EMITTERS DETECTED',hits.length,'signals');add('BEARING CONFIDENCE',(72+noise*22).toFixed(1),'%');add('RECEIVER STATE','PASSIVE / WIDEBAND','');
 }else if(modality==='star_tracker'){
  add('STAR FIXES',5+Math.floor(noise*4),'stars');add('ATTITUDE RESIDUAL',(0.8+noise*1.2).toFixed(2),'arcsec');add('UPDATE RATE',10,'Hz');add('REFERENCE FRAME','INERTIAL / J2000','');
 }else if(modality==='lasercom'||modality==='telemetry'){
  add('LOCAL RELAY',source?source.name:'NO LOCAL SHARED SOURCE','');add('LINK QUALITY',source?(source.linkQuality*100).toFixed(1):'0.0','%');
  add('NOMINAL DATA RATE',source?'2.4':'0','Gb/s');add('POINTING / QUEUE ERROR',(1+noise*4).toFixed(2),'µrad / ms');
 }else if(modality==='imu'||modality==='dvl'){
  add('HEADING',h.toFixed(2),'deg');add('VELOCITY',speed.toFixed(4),'map units/s');add('POSITION FIX',Number(unit.x).toFixed(4)+', '+Number(unit.y).toFixed(4),'normalized');
  add('BIAS ESTIMATE',(0.02+noise*.04).toFixed(3),'deg/h');if(modality==='dvl')add('BOTTOM LOCK',depth>0?'SIMULATED LOCK':'WATER TRACK','');
 }else if(modality==='depth'){
  add('DEPTH',depth.toFixed(1),'m');add('PRESSURE',(1+depth/10.08).toFixed(1),'dbar');add('SAMPLE RATE',10,'Hz');
 }else if(modality==='ctd'){
  add('WATER TEMPERATURE',(12+noise*8-depth/8000).toFixed(2),'°C');add('SALINITY',(34.4+noise*.6).toFixed(2),'PSU');
  add('PRESSURE',(1+depth/10.08).toFixed(1),'dbar');add('CONDUCTIVITY',(4.2+noise*.35).toFixed(3),'S/m');
 }else if(modality==='magnetometer'){
  add('TOTAL FIELD',(48000+noise*1800).toFixed(0),'nT');add('ANOMALY',((noise-.5)*85).toFixed(1),'nT');add('GEOLOGY FLAG',noise>.72?'ANOMALOUS':'BACKGROUND','');
 }else if(modality==='encoders'){
  add('ACTIVE JOINTS',12,'axes');add('ENCODER RESOLUTION',65536,'counts/rev');add('JOINT POSITION RMS',(0.03+noise*.02).toFixed(3),'deg');add('FEEDBACK RATE',500,'Hz');
 }else if(modality==='force_torque'){
  add('END-EFFECTOR LOAD',(12+noise*38).toFixed(1),'N');add('TORQUE',(1+noise*8).toFixed(2),'N·m');add('OVERLOAD MARGIN',(100-noise*18).toFixed(1),'%');
 }else if(modality==='power'){
  add('DC BUS VOLTAGE',(1100+noise*18).toFixed(1),'V');add('BUS CURRENT',(80+speed*500).toFixed(1),'A');add('LOAD POWER',(88+noise*14).toFixed(1),'kW');add('THERMAL MARGIN',(100-noise*10).toFixed(1),'%');
 }else if(modality==='materials'){
  add('STRUCTURAL TEST STATE',daedalusRD&&daedalusRD.materials?'QUALIFIED / DAEDALUS ENGINEERING':'NO QUALIFIED TEST','');
  if(daedalusRD&&daedalusRD.materials){
   add('TEST MATERIAL',daedalusRD.materials.data.name||'—','');
   add('STRESS',Number(daedalusRD.materials.data.stress_mpa||0).toFixed(3),'MPa');
   add('ELASTIC STRAIN',Number(daedalusRD.materials.data.strain_microstrain||0).toFixed(2),'µε');
   add('YIELD UTILIZATION',Number(daedalusRD.materials.data.yield_utilization_percent||0).toFixed(2),'%');
  }
 }else if(modality==='specimen_analysis'){
  add('REMOTE PROBE PAYLOAD',daedalusRD&&daedalusRD.specimen?'ANALYSIS QUALIFIED':'STANDBY','');
  if(daedalusRD&&daedalusRD.specimen){
   add('SPECIMEN',daedalusRD.specimen.data.name||'—','');
   add('SCAN MODE',String(daedalusRD.specimen.data.scan_mode||'').toUpperCase(),'');
   add('SELECTED SECTION',String(daedalusRD.specimen.data.section||'').toUpperCase(),'');
   add('MAGNIFICATION',Number(daedalusRD.specimen.data.magnification_x||0),'×');
   add('MASS',Number(daedalusRD.specimen.data.mass_kg||0).toFixed(2),'kg');
  }
 }else if(modality==='life_support'){
  add('CABIN PRESSURE',101.3,'kPa');add('O₂ PARTIAL PRESSURE',21.2,'kPa');add('CO₂',.08,'%');add('CABIN TEMPERATURE',(21+noise*1.4).toFixed(1),'°C');
 }else if(modality==='radiation'){
  var altitude=Number(unit.orbitalAltitudeKm)||420;add('ORBIT ALTITUDE',altitude,'km');add('TOTAL DOSE RATE',(8+noise*4).toFixed(2),'µGy/h');add('SOLAR PARTICLE ALERT',noise>.9?'ELEVATED':'NOMINAL','');
 }else if(modality==='lidar'||modality==='rangefinder'){
  add('RANGE RETURNS',hits.length,'points');add('RANGE PRECISION',.015,'map units');add('SCAN RATE',20,'Hz');
 }else if(modality==='tracking'||modality==='fire_control'){
  add('TRACK FILES',hits.length,'contacts');add('PRIMARY TRACK',nearest?nearest.contact_id:'NONE','');add('BEARING',nearest?nearest.bearing_deg.toFixed(1):'—','deg');add('SOLUTION QUALITY',nearest?(nearest.confidence*100).toFixed(1):'0.0','%');
 }else if(modality==='environmental'){
  add('AIR TEMPERATURE',(17+noise*9).toFixed(1),'°C');add('PRESSURE',(1008+noise*18).toFixed(1),'hPa');add('WIND',(2+noise*14).toFixed(1),'m/s');add('WEATHER STATUS','SIMULATED LOCAL WEATHER','');
 }else if(modality==='access_alarm'){
  add('ACCESS POINTS',24,'zones');add('OPEN ALARMS',Math.floor(noise*2),'events');add('INTEGRITY','SIMULATED / ONLINE','');
 }else if(modality==='air_data'){
  add('STATIC PRESSURE',(101+noise*2).toFixed(2),'kPa');add('AIR TEMPERATURE',(5+noise*16).toFixed(1),'°C');add('AIRSPEED',(speed*240).toFixed(1),'m/s');
 }else{
  add('HEADING',h.toFixed(1),'deg');add('SPEED',speed.toFixed(4),'map units/s');add('LIVE INPUTS',hits.length,'contacts');
 }
 return rows;
}
function makeFrame(id,sensor,source){
 id=unitId(id);var unit=getUnit(id),pkg=sensorPackages[profileKey(id)];if(!unit||!pkg)return null;
 var def=typeof sensor==='string'?resolveSensor(id,sensor):sensor;if(!def||pkg.sensors.indexOf(def)<0)return null;
 var hits=detections(id,def),rows=measurementRows(id,def,unit,source,hits);
 return {schema:'vigil.fleet.sensor-frame',version:1,unit_id:id,unit_name:pkg.name,unit_profile:profileKey(id),
  sensor_id:id+'-'+def[1].toUpperCase().replace(/[^A-Z0-9]+/g,'-')+'-'+String(pkg.sensors.indexOf(def)+1).padStart(2,'0'),
  sensor_name:def[0],modality:def[1],provenance:'SIMULATED UNIT-OWNED SENSOR // SYNTHETIC ENGINEERING MODEL',
  source_unit_id:id,local_shared_source_id:source?source.id:null,local_shared_source_name:source?source.name:'NO LOCAL SHARED SOURCE',
  local_link_quality:source?source.linkQuality:0,detected_contacts:hits,measurements:rows,timestamp:new Date().toISOString()};
}
function loadRecords(){try{var arr=JSON.parse(localStorage.getItem(STORE)||'[]');return Array.isArray(arr)?arr:[];}catch(e){return [];}}
var reports=loadRecords();
function persist(){try{localStorage.setItem(STORE,JSON.stringify(reports.slice(-MAX_REPORTS)));}catch(e){}}
function sharedReportsFor(id){
 id=unitId(id);
 // Only the mothership receives fleet status summaries. Vehicle sensor frames
 // remain owned by, and displayed on, the originating vehicle.
 if(id!=='DAEDALUS-01')return [];
 var source=localSource(id);if(!source||source.id!=='DAEDALUS-01')return [];
 return reports.filter(function(r){return r&&r.local_shared_source_id==='DAEDALUS-01'&&r.unit_id!=='DAEDALUS-01';}).slice(-8).reverse();
}
function makeUnitReport(id){
 id=unitId(id);var pkg=sensorPackages[profileKey(id)],source=localSource(id);if(!pkg)return null;
 var frames=sensorsForUnit(id).map(function(s){return makeFrame(id,s,source);}).filter(Boolean);
 return {schema:'vigil.fleet.sensor-report',version:1,unit_id:id,unit_name:pkg.name,
  local_shared_source_id:source?source.id:null,local_shared_source_name:source?source.name:'NO LOCAL SHARED SOURCE',
  link_quality:source?source.linkQuality:0,provenance:'SYNTHETIC ENGINEERING MODEL // UNIT-OWNED CHANNELS',
  sensor_count:frames.length,frames:frames,timestamp:new Date().toISOString()};
}
function publishUnitReport(id){
 var report=makeUnitReport(id);if(!report)return {ok:false,reason:'No sensor package or active vehicle state for '+id};
 reports.push(report);if(reports.length>MAX_REPORTS)reports.splice(0,reports.length-MAX_REPORTS);persist();
 if(typeof window.vigilRecordUnitSensorFeed==='function')report.frames.forEach(function(frame){window.vigilRecordUnitSensorFeed(frame);});
 if(window.CorelessRDLabBus&&typeof window.CorelessRDLabBus.publish==='function'){
  window.CorelessRDLabBus.publish('fleet-unit-sensor-report',report);
  if(report.local_shared_source_id)window.CorelessRDLabBus.publish('fleet-shared-source-relay',{
   source_id:report.local_shared_source_id,source_name:report.local_shared_source_name,reporting_unit_id:report.unit_id,
   sensor_count:report.sensor_count,track_count:report.frames.reduce(function(n,f){return n+f.detected_contacts.length;},0),
   timestamp:report.timestamp,provenance:'UNIT-OWNED SENSOR DATA RELAYED THROUGH LOCAL SHARED SOURCE'
  });
 }
 window.dispatchEvent(new CustomEvent('vigil:fleet-sensor-update',{detail:{unit_id:id,source_id:report.local_shared_source_id,timestamp:report.timestamp}}));
 return {ok:true,report:report};
}
function publicApi(){
 return {schema:'vigil.fleet-sensor-network',version:1,packages:sensorPackages,
  getLocalSharedSource:localSource,getUnitPackage:function(id){var p=sensorPackages[profileKey(id)];return p?{name:p.name,sensors:sensorsForUnit(id).slice()}:null;},
  getFrame:function(id,station){return makeFrame(id,resolveSensor(id,station),localSource(id));},
  getUnitReport:makeUnitReport,getSharedReports:sharedReportsFor,publishUnitReport:publishUnitReport,
  getRecords:function(){return reports.slice();}};
}
window.vigilFleetSensorNetwork=publicApi();
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function activeId(){var u=window.vigilGetActiveSimulationUnit&&window.vigilGetActiveSimulationUnit();return unitId(u&&u.id||'ship');}
function activeStation(){var d=window.vigilGetActiveSensorDisplay&&window.vigilGetActiveSensorDisplay();return d&&d.sensor||'';}
function styles(){
 if(document.getElementById('vfsn-style'))return;
 var st=document.createElement('style');st.id='vfsn-style';st.textContent=
 '.vfsn-panel{border:1px solid #357e60;background:linear-gradient(160deg,#061b13,#020805);padding:10px;margin:12px 0;color:#c8f2d9;font-family:"Courier New",monospace}.vfsn-head{display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;align-items:center;border-bottom:1px solid #245e42;padding-bottom:8px;margin-bottom:9px}.vfsn-head b{font-size:11px;letter-spacing:1.2px;color:#9dffd0}.vfsn-head small,.vfsn-head span{font-size:9px;color:#7bab91}.vfsn-columns{display:grid;grid-template-columns:minmax(0,1.45fr) minmax(230px,.75fr);gap:9px}.vfsn-box{border:1px solid #1f553b;background:#020a06;padding:9px;min-width:0}.vfsn-subhead{color:#82dca7;font-size:9px;letter-spacing:1px;margin-bottom:7px}.vfsn-roster{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}.vfsn-sensor{border:1px solid #163e2a;background:#010704;padding:7px;min-width:0}.vfsn-sensor.active{border-color:#e5c77d;box-shadow:inset 0 0 0 1px #e5c77d33}.vfsn-sensor strong{font-size:9px;line-height:1.4;color:#c1f1d4;display:block;margin-bottom:5px}.vfsn-sensor small{display:block;font-size:8px;color:#80ae95;margin-top:3px}.vfsn-measure{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:5px;font-size:8px;border-top:1px solid #102d1f;padding:3px 0}.vfsn-measure span{color:#77a88d;overflow-wrap:anywhere}.vfsn-measure b{color:#e0f8e9;text-align:right;font-weight:normal;overflow-wrap:anywhere}.vfsn-source{font-size:9px;line-height:1.55;color:#c5e7d3}.vfsn-source strong{color:#f1d99b;display:block;font-size:11px}.vfsn-source .vfsn-status{color:#8cffb6}.vfsn-services{margin:7px 0 0;padding-left:15px;color:#80ad91;font-size:8px;line-height:1.6}.vfsn-reports{max-height:250px;overflow:auto}.vfsn-report{border-top:1px solid #173f2b;padding:7px 0;font-size:8px;line-height:1.55;color:#9bc8aa}.vfsn-report b{color:#c7f2d8}.vfsn-actions{display:flex;gap:7px;flex-wrap:wrap;margin-top:9px}.vfsn-actions button{background:#0b3523;color:#baf6d0;border:1px solid #3b8c63;padding:8px 10px;font:9px "Courier New",monospace;cursor:pointer}.vfsn-foot{font-size:8px;line-height:1.55;color:#749b83;margin:9px 0 0}.vfsn-empty{color:#789982;font-size:9px;line-height:1.5;padding:6px 0}@media(max-width:720px){.vfsn-columns{grid-template-columns:1fr}.vfsn-roster{grid-template-columns:1fr}}';
 document.head.appendChild(st);
}
var root=null,lastUnit='';
function createUI(){
 var context=document.getElementById('vigil-unit-sensor-profile');if(!context||document.getElementById('vigil-fleet-sensor-network-ui'))return;
 styles();root=document.createElement('section');root.id='vigil-fleet-sensor-network-ui';root.className='vfsn-panel';
 root.innerHTML='<div class="vfsn-head"><div><b>PLATFORM SENSOR NETWORK // OWN DATA + LOCAL RELAY</b><br><small id="vfsn-platform">PLATFORM INITIALIZING</small></div><span>SIMULATED MEASUREMENTS // UNIT-SCOPED</span></div><div class="vfsn-columns"><div class="vfsn-box"><div class="vfsn-subhead">THIS PLATFORM // INSTALLED SENSOR ARRAY</div><div id="vfsn-roster" class="vfsn-roster"></div><div class="vfsn-actions"><button type="button" id="vfsn-publish">PUBLISH COMPLETE UNIT SENSOR REPORT</button><span id="vfsn-last-publish" class="vfsn-foot">REPORT BUS STANDBY</span></div></div><div class="vfsn-box"><div class="vfsn-subhead">LOCAL SHARED SOURCE // NEAREST AVAILABLE</div><div id="vfsn-source" class="vfsn-source"></div><div class="vfsn-subhead" id="vfsn-relay-heading" style="margin-top:12px">FLEET STATUS // TELEMETRY ONLY</div><div id="vfsn-reports" class="vfsn-reports"></div></div></div><p class="vfsn-foot">Each vehicle owns a distinct sensor package and generates its own measurements from its own simulated state. Vehicle sensor frames stay on their originating platform. Daedalus receives fleet status and telemetry summaries through its local relay; shared sources provide communications, timing and reference services, not live sensor displays from other vehicles. Data are simulation outputs, not physical sensor readings. Browser-local reports are not yet synchronized between separate multiplayer clients.</p>';
 context.appendChild(root);
 root.querySelector('#vfsn-publish').addEventListener('click',function(){
  var id=activeId(),result=publishUnitReport(id),status=root.querySelector('#vfsn-last-publish');
  status.textContent=result.ok?'REPORT PUBLISHED // '+result.report.sensor_count+' OWN SENSOR CHANNELS // '+result.report.timestamp:'PUBLISH FAILED // '+result.reason;render();
 });
}
function render(){
 if(!root||!document.body.contains(root))return;
 var id=activeId(),key=profileKey(id),pkg=sensorPackages[key],source=localSource(id),unit=getUnit(id);
 if(!pkg||!unit){root.querySelector('#vfsn-platform').textContent='NO ASSIGNED PLATFORM SENSOR MODEL';return;}
 var selected=activeStation(),currentDef=resolveSensor(id,selected),frames=sensorsForUnit(id).map(function(s){return makeFrame(id,s,source);}).filter(Boolean);
 root.querySelector('#vfsn-platform').textContent=pkg.name+' // '+id+' // '+frames.length+' INSTALLED CHANNELS';
 root.querySelector('#vfsn-roster').innerHTML=frames.map(function(frame){
  var isActive=!!currentDef&&frame.sensor_name===currentDef[0],rows=frame.measurements.slice(0,isActive?6:3);
  return '<article class="vfsn-sensor'+(isActive?' active':'')+'"><strong>'+esc(frame.sensor_name)+'</strong>'+rows.map(function(m){return '<div class="vfsn-measure"><span>'+esc(m.label)+'</span><b>'+esc(m.value)+(m.units?' '+esc(m.units):'')+'</b></div>';}).join('')+'<small>'+esc(frame.modality.toUpperCase())+' // '+frame.detected_contacts.length+' RETURN(S) // '+esc(frame.provenance)+'</small></article>';
 }).join('');
 if(source){
  var pos=Number(source.distance||0);
  root.querySelector('#vfsn-source').innerHTML='<strong>'+esc(source.name)+'</strong><div class="vfsn-status">LOCAL LINK ACQUIRED // '+(source.linkQuality*100).toFixed(1)+'% LINK QUALITY</div><div>PROVIDER: '+esc(source.kind)+' // '+pos.toFixed(4)+' REGIONAL UNITS</div><ul class="vfsn-services">'+source.services.map(function(s){return '<li>'+esc(s)+'</li>';}).join('')+'</ul>';
 }else{
  root.querySelector('#vfsn-source').innerHTML='<strong>NO LOCAL SHARED SOURCE</strong><div>Vehicle is outside the coverage area of Daedalus and FAC-01. Own sensors remain fully operational; shared services are unavailable until a relay is in range.</div>';
 }
 var shared=sharedReportsFor(id),relayHeading=root.querySelector('#vfsn-relay-heading'),relayList=root.querySelector('#vfsn-reports');
 if(id==='DAEDALUS-01'){
  relayHeading.textContent='FLEET STATUS // TELEMETRY ONLY';
  relayList.innerHTML=shared.length?shared.map(function(r){
   var contacts=(r.frames||[]).reduce(function(n,f){return n+(Array.isArray(f.detected_contacts)?f.detected_contacts.length:0);},0);
   return '<div class="vfsn-report"><b>'+esc(r.unit_name)+'</b><br>'+esc(r.sensor_count)+' CHANNELS ONLINE // '+contacts+' TRACK RETURNS REPORTED<br>'+esc(r.timestamp)+'</div>';
  }).join(''):'<div class="vfsn-empty">NO VEHICLE STATUS REPORTS RECEIVED THROUGH DAEDALUS LOCAL RELAY YET. INDIVIDUAL SENSOR FRAMES REMAIN ON THEIR ORIGINATING VEHICLES.</div>';
 }else{
  relayHeading.textContent='SHARED SERVICES // NO PEER SENSOR STREAMS';
  relayList.innerHTML='<div class="vfsn-empty">THIS CONSOLE DISPLAYS THIS PLATFORM OWN SIMULATION-FED SENSOR CHANNELS ONLY. THE LOCAL SOURCE PROVIDES COMMUNICATIONS, TIMING AND REFERENCE SERVICES; OTHER VEHICLE SENSOR FRAMES ARE NOT STREAMED INTO THIS DISPLAY.</div>';
 }
 if(id!==lastUnit){lastUnit=id;publishUnitReport(id);}
}
function installOnboardDeck(){
 // R&D is main navigation item 15. Keep its panel in the main page layout.
 // Do not move it into Simulation Bay or hide it based on active vehicle.
}
function boot(){
 installOnboardDeck();createUI();render();
 window.addEventListener('vigil:active-unit-changed',function(){render();});
 window.addEventListener('vigil:simulation-unit-state-changed',function(){render();});
 window.addEventListener('vigil:fleet-sensor-update',function(){render();});
 window.addEventListener('vigil:daedalus-rd-update',function(){render();});
 window.setInterval(function(){
  var ids=['DDG-51','DAEDALUS-01','DRONE-01','UUV-01','SSN-774','MECH-01','FAC-01'];
  ids.forEach(function(id){publishUnitReport(id);});
  render();
 },30000);
 window.setInterval(render,1800);
 // Seed the local relay archives on first startup so each coverage zone has useful shared telemetry.
 if(!reports.length){
  ['DDG-51','DAEDALUS-01','DRONE-01','UUV-01','SSN-774','MECH-01','FAC-01'].forEach(function(id){publishUnitReport(id);});
  render();
 }
 // Re-publish after deferred R&D code has initialized the shared bus.
 window.setTimeout(function(){['DDG-51','DAEDALUS-01','DRONE-01','UUV-01','SSN-774','MECH-01','FAC-01'].forEach(function(id){publishUnitReport(id);});render();},1800);
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();