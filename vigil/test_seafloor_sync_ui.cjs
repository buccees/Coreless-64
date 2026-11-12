const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const html = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");
const submersible = fs.readFileSync(path.join(__dirname, "..", "vigil-submersible-3d-view.js"), "utf8");
const mechView = fs.readFileSync(path.join(__dirname, "..", "vigil-mech-3d-view.js"), "utf8");
const mechGarage = fs.readFileSync(path.join(__dirname, "..", "vigil-mech-garage.js"), "utf8");
const otherVehicleViews = fs.readFileSync(path.join(__dirname, "..", "vigil-independent-vehicle-3d-views.js"), "utf8");
const scyllaHelicopter = fs.readFileSync(path.join(__dirname, "..", "vigil-scylla-helicopter.js"), "utf8");
const fleetSensorNetwork = fs.readFileSync(path.join(__dirname, "..", "vigil-fleet-sensor-network.js"), "utf8");
new Function(submersible);
new Function(mechView);
new Function(mechGarage);
new Function(otherVehicleViews);
new Function(fleetSensorNetwork);
new Function(scyllaHelicopter);
for (const required of [
  "SCYLLA // ROTORCRAFT COMBAT SIMULATOR",
  "scylla-heli-open",
  "SCYLLA AIRFRAME ACTIVE",
  "TACTICAL RADAR // 360",
  "COLLECTIVE +",
  "GUIDED MISSILE",
  "AIR SUPERIORITY",
]) assert.ok(scyllaHelicopter.includes(required), "missing SCYLLA helicopter mode contract: " + required);
assert.ok(html.includes("vigil-scylla-helicopter.js?v=11"), "expected SCYLLA-only helicopter mode script");
for (const required of [
  "heli-pc-capture",
  "CAPTURE MOUSE",
  "requestPointerLock",
  "pointerlockchange",
  "e.movementX",
  "e.movementY",
  "mouseFlight.locked?mouseFlight.x",
  "mouseFlight.locked?-mouseFlight.y",
  "DESKTOP KEYBOARD + MOUSE",
  "MOBILE TOUCH / GYRO",
  "pointerlockerror",
  "exitPointerLock",
  "mouseFlight.sensitivity",
  "performance.now()",
]) assert.ok(scyllaHelicopter.includes(required), `missing SCYLLA desktop mouse control marker: ${required}`);
for (const required of [
  "heli-pc-controls",
  "PC PILOT // FLIGHT INPUT",
  "data-key=\"w\"",
  "data-key=\"a\"",
  "data-key=\"s\"",
  "data-key=\"d\"",
  "DESKTOP KEYBOARD",
  "MOBILE TOUCH / GYRO",
  "(min-width: 851px) and (pointer: fine)",
  "function updatePcKey(k,on)",
  "keys[k]=true;updatePcKey(k,true)",
]) assert.ok(scyllaHelicopter.includes(required), `missing desktop-only SCYLLA keyboard control marker: ${required}`);
assert.ok(scyllaHelicopter.includes("heli-touch-controller"), "missing SCYLLA mobile on-screen flight controller");
assert.ok(scyllaHelicopter.includes("function initTerrain3D()"), "missing live WebGL terrain renderer");
assert.ok(scyllaHelicopter.includes("function drawTerrainFallback(w,h)"), "missing 2D terrain fallback when WebGL is unavailable");
assert.ok(scyllaHelicopter.includes("if(!terrainReady)drawTerrainFallback(w,h)"), "flight scene must remain visible when WebGL initialization fails");
assert.ok(scyllaHelicopter.includes("holds.fire=true;fire();"), "fire controls must respond to a quick tap, not only a sustained hold");
assert.ok(scyllaHelicopter.includes("NO TARGET IN FORWARD ACQUISITION CONE"), "target-lock control must report unsuccessful acquisition");
assert.ok(scyllaHelicopter.includes("function releaseStick(){"), "missing safe stick-release handler used during focus loss");
assert.ok(scyllaHelicopter.includes("function renderTerrain3D()"), "missing continuously updated 3D flight terrain");
assert.ok(scyllaHelicopter.includes("heli-instrument-deck"), "cockpit readouts must live in a dedicated lower instrument deck");
assert.ok(scyllaHelicopter.includes("heliDeck.appendChild(heliHud)"), "flight metrics must be below the 3D view");
assert.ok(scyllaHelicopter.includes("heliDeck.appendChild(heliSide)"), "tactical/system readouts must be below the 3D view");
assert.ok(scyllaHelicopter.includes("heliFlightPane.hidden=true"), "duplicate directional control panel must not cover the phone cockpit");
assert.ok(scyllaHelicopter.includes("flex:0 0 164px"), "lower cockpit deck must reserve compact readout space");

assert.ok(scyllaHelicopter.includes("scylla-heli-terrain-3d"), "missing separate WebGL scene layer beneath the live cockpit HUD");
assert.ok(scyllaHelicopter.includes("function terrainElevation(wx,wz)"), "missing simulation-generated terrain elevation model");
assert.ok(scyllaHelicopter.includes("gl.drawElements(gl.TRIANGLES"), "terrain must be rendered as 3D geometry, not a static background");

assert.ok(scyllaHelicopter.includes("heli-gyro-panel"), "missing SCYLLA phone gyroscope flight controls");
assert.ok(scyllaHelicopter.includes("requestFullscreen"), "missing SCYLLA full-screen control");
assert.ok(scyllaHelicopter.includes("data-hold"), "missing SCYLLA on-screen control actions");

for (const required of [
  "function updateLaunchButton()",
  "window.addEventListener('vigil:active-unit-changed',updateLaunchButton)",
  "launch.textContent=label?'LAUNCH '+label+' 3D VIEW':'FACILITY // NO PILOT VIEW'",
  "mech:'MECH'",
  "submersible:'UUV'",
  "submarine:'SUBMARINE'",
  "ship:'SHIP'",
  "drone:'DRONE'",
  "mothership:'DAEDALUS'",
  "if(activeUnit==='mech')",
  "if(activeUnit!=='submersible')",
]) {
  assert.ok(submersible.includes(required), `missing per-vehicle launch routing marker: ${required}`);
}
assert.ok(!html.includes("launchButton.textContent='LAUNCH '+unitId.toUpperCase()"), "sensor workspace must not overwrite the per-vehicle launch router");
for (const required of [
  "function publishMechSimulationSensors()",
  "function fuseSpatialObservations(snapshot)",
  "height:100dvh",
  "var compassPane=root.querySelector('#m3-compass-pane');if(compassPane)root.appendChild(compassPane)",
  "if(controls.dataset.signature!==signature||controls.children.length!==6){",
  "controls.replaceChildren();controls.dataset.signature=signature;",
  "GYRO STABILIZATION / WEAPON ASSIST",
  "function commandWeaponGroup(action)",
  "function buildWeaponHud(b)",
  "function updateWeaponHud()",
  "function updateWeaponReticle()",
  "function roleReadoutValues(b)",
  "function renderRoleReadouts(b)",
  "m3-role-readouts",
  "SCOUT // PANORAMIC RECON DISPLAY",
  "SOLDIER // FRONT-LINE COMBAT DISPLAY",
  "DEFENDER // PROTECTED COMBAT DISPLAY",
  "SNIPER // PRECISION FIRE CONTROL",
  "HEAVY GUNNER // INDIRECT-FIRE CONTROL",
  "TACTICS COMMANDER // NETWORK COMMAND DISPLAY",
  "Twin Rotary Machine Gun",
  "Breach Shotgun",
  "Programmable Grenade Launcher",
  "Anti-Armor Rocket Pod",
  "Long-Range Precision Rifle",
  "Automatic Mobile Rifle",
  "Scatter Mine Dispenser",
  "Timed Bomb Rack",
  "Heavy Anti-Armor Cannon",
  "Heavy Missile Launcher",
  "Long-Range Howitzer",
  "Indirect-Fire Mortar",
  "Heavy Sniper Cannon",
  "Close-Quarters Pile Driver",

  "function renderWeaponOpticPip()",
  "m3-weapon-groups",
  "m3-role-display",
  "m3-weapon-pip",
  "vigilSetMechWeaponGroup",
  "HIGH-ANGLE / BALLISTIC SCOPE",
  "MISSILE TRACKING BOX",
  "SNIPER OPTIC / RANGEFINDER",
  "TRACKING CIRCLE / SPREAD BLOOM",
  "Math.min(Number(current&&current.max_speed)||.03,v+Number(item[2]))",


  "m3-flightline",
  "m3-speed",
  "m3-target-speed",
  "m3-max-speed",
  "m3-tactical-map-canvas",
  "m3-map-local",
  "m3-map-regional",
  "m3-drive-pad",
  "data-drive=\"forward\"",
  "m3-compass-track",
  "function drawTacticalMap(force)",
  "function bindMechScreenControls()",
  "function handleMechPilotKey(e)",
  "SIM UNITS / S · ACTUAL",
  "height:100dvh!important",
  "document.body.style.overflow='hidden'",
  "overflow:hidden!important",
  "window.vigilGetMechFusedSpatialModel=function()",
  "m3-spatial-fusion-pane",
  "m3-fusion-track-list",
  "ACTIVE SENSOR CAPABILITIES",
  "vigilFleetSensorNetwork.getUnitPackage",
  "vigilRecordUnitSensorFeed(frame)",
]) {
  assert.ok(mechView.includes(required), `missing simulation-fed mech fusion cockpit marker: ${required}`);
}
for (const required of [
  "window.vigilSetMechWeaponGroup=function",
  "window.vigilGetMechGarageState=function",
  "builds.forEach(function(b){b.role=role(b)",
  "b.weaponGroups=b.weaponGroups||{}",
]) {
  assert.ok(mechGarage.includes(required), `missing per-build HOUND role / weapon-group persistence marker: ${required}`);
}
for (const required of [
  "HOUND 2.4 GHz WI-FI CSI / RF MOTION RADAR",
  "'wifi_csi'",
  "RF CENTER FREQUENCY",
  "DOPPLER MOTION ENERGY",
  "POSITION AUTHORITY",
  "detected_contacts:def[1]==='wifi_csi'?[]:hits",
  "installedSensors.findIndex",
]) {
  assert.ok(fleetSensorNetwork.includes(required), `missing simulated 2.4 GHz CSI sensor contract: ${required}`);
}
for (const required of [
  "var vigilMechWeaponProfiles=",
  "magazineRemaining",
  "vigilDamageMechComponent=function",
  "OVERHEAT LOCKOUT",
  "RELOAD COMPLETE",
  "max_speed:Number(unit.maxSpeed)||0",
]) {
  assert.ok(html.includes(required), `missing HOUND simulated weapon telemetry / damage contract: ${required}`);
}
for (const required of [
  "m3-environment-webgl",
  "function initEnvironmentRenderer()",
  "function renderEnvironment(b)",
  "NO ENVIRONMENT SENSOR FITTED",
  "ACTIVE SENSOR CAPABILITIES",
  "AS-THERM",
  "AS-NV",
  "AS-MINE",
  "renderEnvironment(selectedBuild)",
  "vigilGetSensorInputSnapshot",
  "o.unit_id!==unitId",
  "o.feed_stale",
  "o.normalized_position",
]) {
  assert.ok(mechView.includes(required), `missing sensor-fused mech environment renderer marker: ${required}`);
}
assert.ok(html.includes('vigil-mech-3d-view.js?v=14'), "expected cache-busted first-person mech pilot renderer script");
assert.ok(/vigil-mech-garage\.js\?v=13/.test(html), "expected cache-busted mech garage and role metadata script");
assert.ok(/vigil-fleet-sensor-network\.js\?v=(daedalus-orbital-7|daedalus-orbital-8)/.test(html), "expected cache-busted fleet sensor network script");
for (const required of [
  "window.vigilOpenMech3DView=open",
  "SCYLLA // MECH CONTROL STATION",
  "var scyllaHost=document.getElementById('scylla-security-panel')||document.body;scyllaHost.appendChild(root);",
]) {
  assert.ok(mechView.includes(required), `missing SCYLLA-hosted mech control screen marker: ${required}`);
}
for (const required of [
  'id="scylla-open-mech-controls"',
  "window.vigilOpenMech3DView('MECH-01')",
  'id="scylla-mech-control-launch"',
]) {
  assert.ok(html.includes(required), `missing SCYLLA mech control entrypoint: ${required}`);
}
for (const required of [
  "ship:{title:",
  "drone:{title:",
  "submarine:{title:",
  "mothership:{title:",
  "window.vigilOpenOtherVehicle3DView=open",
]) {
  assert.ok(otherVehicleViews.includes(required), `missing independent vehicle pilot view marker: ${required}`);
}
for (const required of [
  'm3-first-person-stage',
  'FIRST-PERSON PILOT VIEW // SIMULATION TERRAIN + UNIT SENSOR OVERLAYS',
  'window.vigilGetWorldTerrainAt',
  'window.vigilAdvancePlanetPoint',
  'function renderEnvironment(b)',
  'function draw(){if(!active)return;renderEnvironment(selectedBuild);updateMechCompass(getUnit());}',
  'FIRST-PERSON PILOT',
  'NO ENVIRONMENT SENSOR FITTED',
  'NO RF/CSI SENSOR FEED',
]) {
  assert.ok(mechView.includes(required), `missing first-person mech pilot contract: ${required}`);
}
assert.ok(!mechView.includes("capabilityNames.push('HOUND 2.4 GHz WI-FI CSI / RF MOTION RADAR')"),
  "mech cockpit must not invent an installed HOUND sensor feed");
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
assert.ok(html.includes('vigil-submersible-3d-view.js?v=4'), "expected cache-busted vehicle launch router script");
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
  'var rows=64,cols=84,points=[],cameraZ=-Math.sqrt(Math.max(0,depth))*2.3',
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
  "var panelX=16,panelY=18,panelW=Math.min(228,w-32),panelH=compactHud?116:218",
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
  "mapLayers=['FUSED','MULTIBEAM','SIDE-SCAN','SUB-BOTTOM','MAGNETIC','CTD','THERMAL','INFRARED','DVL/INS','FEED INPUTS']",
  "if(mapLayer==='THERMAL')",
  "IR // WATER ATTENUATED · POSITIONED FEED REQUIRED",
  "water_attenuation:'LONG-RANGE IR ATTENUATED BY WATER'",
  "var unlocatedMeasurementLabels=0",
  "o.reference_unit_id===own.id",
  "var hasRangeBearing=o.range_m!==null&&o.range_m!==undefined",
  "height:clamp(64px,8.5vh,94px)!important",
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
  'var movementDistance=ship.speed*dt*movementDistanceScale',
  "var movementDistanceScale=ship.shipClass==='carrier'?.00004:ship.shipClass==='submersible'?.00002:1",
  'var separation=window.vigilGetPlanetRangeBearing(own.x,own.y,other.x,other.y)',
  'var geometry=window.vigilGetPlanetRangeBearing(shooter.x,shooter.y,target.x,target.y)',
  'var distance=Number(fireState.range_normalized)',
  'var cellPoint=window.vigilNormalizePlanetPoint((ix+.5)/42,(iy+.5)/42)',
  'window.vigilGetWorldTerrainAt(sample.x,sample.y)',
  'SPHERICAL STITCHED ATLAS // WRAPPED LONGITUDE AND CONNECTED POLES',
]) {
  assert.ok(html.includes(required) || submersible.includes(required), `missing first-person bathymetry contract in index.html or vigil-submersible-3d-view.js: ${required}`);
}
assert.ok(!html.includes("if(ship.x<.04||ship.x>.96)"), "regional fleet must not bounce off horizontal world boundaries");
assert.ok(!html.includes("if(ship.y<.05||ship.y>.95)"), "regional fleet must not bounce off vertical world boundaries");
console.log(`Validated syntax for ${parsed} inline JavaScript block(s), seafloor sync, navigation helm, rotating sonar, mobile controls, and stitched-planet contracts.`);

assert.ok(scyllaHelicopter.includes("scylla-heli-touch-force"), "missing SCYLLA immersive touch controller");
assert.ok(scyllaHelicopter.includes("screen.requestFullscreen().then"), "missing automatic fullscreen launch");

assert.ok(scyllaHelicopter.includes("deviceorientation"), "missing SCYLLA phone gyroscope input");
assert.ok(scyllaHelicopter.includes("requestPermission"), "missing phone motion permission flow");
assert.ok(scyllaHelicopter.includes("heli-round-weapons"), "missing round weapon selectors");
assert.ok(scyllaHelicopter.includes("heli-touch-fire"), "missing round fire control");
assert.ok(scyllaHelicopter.includes("COLLECTIVE / LIFT"), "collective slider must explain its lift function");
assert.ok(scyllaHelicopter.includes("heli-flight-strip"), "collective control must stay out of the bottom touch-control cluster");
assert.ok(scyllaHelicopter.includes("GYRO LIVE // PITCH"), "phone gyro must provide live flight feedback");
assert.ok(scyllaHelicopter.includes("rawPitch=dg;rawRoll=-db"), "phone gyro axes must remap for landscape orientation");
assert.ok(scyllaHelicopter.includes("var targetPitch=inputPitch*.34"), "cyclic input must be proportional rather than binary");
assert.ok(!scyllaHelicopter.includes('id="heli-stick"'), "phone mode must not expose a directional joystick");
assert.ok(mechView.includes("m3-chopper-mode"), "missing SCYLLA mech-to-chopper mode switch");
assert.ok(scyllaHelicopter.includes("window.vigilOpenScyllaChopperMode"), "missing SCYLLA chopper mode entry point");
assert.ok(scyllaHelicopter.includes("MECH-01"), "missing single assigned SCYLLA airframe guard");
assert.ok(scyllaHelicopter.includes("MECH COCKPIT RESTORED"), "missing return-to-mech cockpit transition");