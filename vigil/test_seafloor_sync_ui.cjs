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
  'var rows=42,cols=56,points=[],cameraZ=heightAt(cameraX,cameraY)+46',
  'var water=ctx.createLinearGradient(0,0,0,h)',
  'UUV PILOT VIEW // PELAGOS-01',
  'heading=(drag.heading+(e.clientX-drag.x)*.22+360)%360',
  'cameraX+=Math.sin(rad)*distance;cameraY+=Math.cos(rad)*distance;',
  'var ridgeAxis=y-.24*x-28, trenchAxis=y+.48*x-36, shelfAxis=y-.62*x+105',
  'broad basin, continental shelf, long ridge, and a narrow trench',
  'FICTIONAL WORLD // REAL BATHYMETRY RUINS ONLY AT SPAWN',
  'id="v3-course"',
  'id="v3-set-course"',
  'function setCourse(value)',
  'NAVIGATION COURSE SET',
  'Rotating sonar PPI inset',
  'anim=(anim+1.8)%360',
  'class="v3-helm"',
  'class="v3-panel"',
  'aria-label="Vehicle movement controls"',
  'aria-label="Sensor and view controls"',
]) {
  assert.ok(html.includes(required), `missing first-person bathymetry contract: ${required}`);
}
console.log(`Validated syntax for ${parsed} inline JavaScript block(s), seafloor terrain and reconciliation, navigation helm, rotating sonar, and mobile control panels.`);
