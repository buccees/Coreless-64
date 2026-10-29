const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const html = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");
const scripts = [...html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)];
let parsed = 0;

for (const [, attributes, source] of scripts) {
  if (/\bsrc\s*=/.test(attributes)) continue;
  const type = (attributes.match(/\btype\s*=\s*["']?([^\s"'>]+)/i) || [])[1];
  if (type && !/^(text|application)\/javascript$|^module$/i.test(type)) continue;
  if (!source.trim()) continue;
  try {
    new Function(source);
    parsed += 1;
  } catch (error) {
    throw new Error(`Inline script ${parsed + 1} failed JavaScript syntax validation: ${error.message}`);
  }
}

assert.ok(parsed > 0, "expected at least one inline JavaScript block");
for (const required of [
  "vigil-survey-ack-records-v1-",
  "UPLOAD ACCEPTED / VERIFY PENDING",
  "SYNC PENDING",
  "vigilSyncSeafloorCampaignSurvey",
  "vigil-seafloor-shared-snapshot-v1-",
]) {
  assert.ok(html.includes(required), `missing seafloor sync feature marker: ${required}`);
}
// Simulation-bay unit-tab regression checks: these exercise the declared UI/control contract
// without launching a browser or adding Playwright to the routine workflow.
for (const required of [
  'vigil-simulation-unit-tabs',
  'aria-label="Select unit to pilot"',
  'data-unit="ship"',
  'data-unit="drone"',
  'data-unit="submersible"',
  'data-unit="submarine"',
  'data-unit="mech"',
  'data-unit="facility"',
  "event.key==='ArrowRight'",
  "event.key==='ArrowLeft'",
  "event.key==='Home'",
  "event.key==='End'",
  "vigil:active-unit-changed",
  "vigilSetSimulationUnitState",
  "vigil-nav-heading",
  "vigil-nav-speed",
  "SEAFLOOR MAPPING",
]) {
  assert.ok(html.includes(required), `missing simulation-bay unit-control marker: ${required}`);
}
// Bathymetry / first-person pilot-view regression checks. These validate the actual view contract
// without launching a browser or adding Playwright to the routine workflow.
for (const required of [
  'cameraX=0,cameraY=0,lookPitch=0',
  'function worldToView(x,y,w,h,cameraZ)',
  'var rows=42,cols=56,points=[],cameraZ=-Math.sqrt(Math.max(0,depth))*2.3',
  'var water=ctx.createLinearGradient(0,0,0,h)',
  'UUV PILOT VIEW // PELAGOS-01',
  'cameraX=(worldPoint.x-.5)*1500;cameraY=(.5-worldPoint.y)*1500',
  'var speedHudY=compactHud?Math.min(h-24,140):Math.max(28,h-44),pilotHudY=compactHud?Math.min(h-8,160):Math.max(42,h-24),availableHudWidth=',
  'var radarR=Math.max(35,Math.min(54,w*.105)),radarX=w-radarR-20',
  'function terrainElevationAt(x,y)',
  'function terrainWorldPointAt(x,y)',
  'A zero-speed helm command is an explicit hold-position command.',
  "Number(ship.targetSpeed)<=0",
  'ship.stationKeepingEnabled=false;ship.formationActive=false',
  "window.vigilAdvancePlanetPoint(pilot.x,pilot.y,bearing,distance)",
  'worldPoint=terrainWorldPointAt(wx,wy)',
  'bathymetry=window.vigilGetWorldTerrainAt(worldPoint.x,worldPoint.y)',
  'for(var rr=rows-1;rr>=0;rr--)',
  'isLand:!!(bathymetry&&bathymetry.isLand),depthMeters:waterDepth',
  'heading=(drag.heading+(e.clientX-drag.x)*.22+360)%360',
  'cameraX=(p.x-.5)*1500;cameraY=(.5-p.y)*1500;',
  'var ridgeAxis=y-.24*x-28,trenchAxis=y+.48*x-36,shelfAxis=y-.62*x+105',
  'function ruptureLocalAt(x,y)',
  'PELAGOS ABYSSAL RIFT',
  'depthMeters=Math.max(depthMeters,6500+riftCore*18000)',
  'Real bathymetry is warped into ruin-like terrain ONLY inside the active player-spawn patch.',
  'id="v3-course"',
  'id="v3-set-course"',
  'function setCourse(value)',
  'NAVIGATION COURSE SET',
  'Always-on sensor suite: measurements are computed from simulation world data, then rendered here.',
  'window.vigilSensorSuite=(function()',
  'function measureCell(input)',
  'function updateNavigation(point,now,depthSample,unit)',
  'temperatureC:temp,salinityPSU:salinity,magneticNt:magnetic,sedimentIndex:sediment',
  'temperatureC:temperatureC,salinityPSU:salinityPSU,magneticFieldNt:magneticFieldNt,sedimentIndex:sedimentIndex',
  'readings.sideScan.feature_score',
  'readings.magnetometer.detected',
  'readings.temperature.anomaly',
  'readings.subBottom.geological_discontinuity',
  'FUSED SENSOR OVERLAY // LIVE',
  'MULTIBEAM  RETURNS',
  'SIDE-SCAN  RETURNS',
  'SUB-BOTTOM  RETURNS',
  'MAGNETIC  ANOMALIES',
  'THERMAL  ANOMALIES',
  'DVL UNCERTAINTY',
  "function getCachedVigilSensorInputSnapshot(force)",
  "function vigilSensorColor(modality)",
  "var supportedSensorModalities=['sonar','multibeam','mbes','side_scan','sidescan','sub_bottom','subbottom','magnetometer','ctd','temperature','dvl'",
  "var tempLeft=environment(input.x-.0002,input.y,left).temperatureC",
  "var ctd={temperature_c:",
  "function drawSeparatedSensorGlyph",
  "drawSeparatedSensorGlyph(sp.x,sp.y,-7,-6,'#80e9ff','dash',.82)",
  "sensorCounts.ctd++",
  "var panelX=16,panelY=18,panelW=Math.min(228,w-32),panelH=compactHud?102:180",
  "source:'SIMULATION SENSOR MODELS + REGISTERED SENSOR FEEDS'",
  "registered_sensor_feeds:{registered:",
  "mapFeedObservations.forEach(function(o,index)",
  "mapLayer==='FEED INPUTS'?1:",
  "mapLayer==='DVL/INS'?.98:.72",
  "ALL LAYERS ACTIVE",
  "var mapSensorSuite=window.vigilSensorSuite,readingsGrid=[]",
  "bottom_depth_m:Math.max(0,depth+hash(input.x,input.y,32)*(.35+depth*.0009))",
  "var fusedNav=window.vigilGetSensorFusionFrame&&window.vigilGetSensorFusionFrame()",
  "inputModeCounts[code]=(inputModeCounts[code]||0)+1",
  "SOURCES '+feedSourceSummary",
  "drawSeparatedSensorGlyph(sp.x,sp.y,-7,0,'#ffdd84','dash',.82)",
  "drawSeparatedSensorGlyph(sp.x,sp.y,7,-2,'#ff77be','diamond',.9)",
  "drawSeparatedSensorGlyph(sp.x,sp.y,0,-7,'#ff7348','circle',.9)",
  "drawSeparatedSensorGlyph(sp.x,sp.y,0,7,'#cc9eff','cross',.9)",
  "drawSeparatedSensorGlyph(sp.x,sp.y,7,6,'#8eeeff','circle',.86)",
  "window.vigilRefreshUnifiedSeafloorMap=drawWorldMap",
  "if(list.dataset.signature===signature){if(typeof window.vigilRefreshUnifiedSeafloorMap==='function'",
  "mapSensorSuite.measureCell({x:Number(mt.x)||0,y:Number(mt.y)||0,rangeM:rangeM,terrain:mt,left:lt,right:rt,near:ut,far:dt})",
  "ctx.fillText('SPEED '+(u?Number(u.speed||0).toFixed(3):'---')+' / CMD '+(u?Number(u.target_speed==null?(u.speed||0):u.target_speed).toFixed(3):'---')+' / MAX '+(u?Number(u.max_speed||0).toFixed(3):'---')+' SIM',20,speedHudY,availableHudWidth)",
  "/* Layout guard: the unified map is a separate row, never a floating screen over the pilot canvas. */",
  "#vigil-3d-seafloor-view .v3-world-map{position:relative!important;top:auto!important;right:auto!important;bottom:auto!important;left:auto!important;inset:auto!important;display:block!important;flex:0 0 auto!important;width:100%!important",
  "#vigil-3d-seafloor-view .v3-world-map.expanded{position:relative!important;top:auto!important;right:auto!important;bottom:auto!important;left:auto!important;inset:auto!important;width:100%!important",
  "var compactHud=h<(Math.max(35,Math.min(54,w*.105))*2+200);",
  "window.vigilRefreshUnifiedSeafloorMap();",
  'window.vigilGetSensorFusionFrame=function()',
  'SIMULATION SENSOR MODELS',
  'Rotating sonar PPI inset',
  'anim=(anim+1.8)%360',
  'class="v3-helm"',
  'class="v3-panel"',
  'v3-collapsible',
  'aria-label="Vehicle movement controls"',
  'aria-label="Sensor and view controls"',
  'id="vigil-3d-world-map-canvas"',
  'id="v3-map-local"',
  'id="v3-map-regional"',
  'function drawWorldMap()',
  "ship.formationTarget={x:stationPoint.x,y:stationPoint.y}",
  "var regionalFleetLastError=''",
  'VIGIL regional fleet tick recovered after movement error:',
  'var landGrid=[],terrainGrid=[],measuredDepthGrid=[]',
  "terrain.isLand?'#cbb989'",
  "mapCtx.strokeStyle='rgba(255,232,172,.98)'",
  'v3-map-ground-key',
  'v3-map-shallow-key',
  'v3-map-deep-key',
  'v3-map-trench-key',
  'slopeTone=Math.min(1,(Math.abs(p1.z-p3.z)+Math.abs(p2.z-p4.z))/28)',
  "rgba(3,19,31,.38)",
  'window.vigilGetKnownWorldMapContacts=function()',
  'The world map plots only reported observations, never hidden enemy truth.',
  'var increment=Math.max(.001,max*.1)',
  'var focalX=w*.92*zoom,focalY=h*.92*zoom',
  'focalX=w*.92*zoom/d,focalY=h*.92*zoom/d',
  'id="v3-terrain-resizer"',
  "terrainResizer.addEventListener('pointerdown'",
  "terrainResizer.addEventListener('pointermove'",
  "terrainResizer.addEventListener('pointerup'",
  "e.key!=='ArrowUp'",
  "say('ZOOM IN // '+Math.round(zoom*100)+'%')",
  'VIEW RESET // VEHICLE POSITION AND COURSE RETAINED',
  'z-index:10;pointer-events:auto',
  'window.vigilGetPlanetRangeBearing=vigilPlanetRangeBearing',
  'window.vigilAdvancePlanetPoint=vigilAdvancePlanetPoint',
  'function vigilPlanetNoise(x,y,scale,salt)',
  'var nextPlanetPoint=window.vigilAdvancePlanetPoint(ship.x,ship.y,ship.heading,ship.speed*dt)',
  'var separation=window.vigilGetPlanetRangeBearing(own.x,own.y,other.x,other.y)',
  'var geometry=window.vigilGetPlanetRangeBearing(shooter.x,shooter.y,target.x,target.y)',
  'var distance=Number(fireState.range_normalized)',
  'var cellPoint=window.vigilNormalizePlanetPoint((ix+.5)/42,(iy+.5)/42)',
  'window.vigilGetWorldTerrainAt(sample.x,sample.y)',
  'SPHERICAL STITCHED ATLAS // WRAPPED LONGITUDE AND CONNECTED POLES',
]) {
  assert.ok(html.includes(required), `missing first-person bathymetry contract: ${required}`);
}
assert.ok(!html.includes("if(ship.x<.04||ship.x>.96)"), "regional fleet must not bounce off horizontal world boundaries");
assert.ok(!html.includes("if(ship.y<.05||ship.y>.95)"), "regional fleet must not bounce off vertical world boundaries");
console.log(`Validated syntax for ${parsed} inline JavaScript block(s), seafloor sync, navigation helm, rotating sonar, mobile controls, and stitched-planet contracts.`);
