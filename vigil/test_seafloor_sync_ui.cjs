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
console.log(`Validated syntax for ${parsed} inline JavaScript block(s) and seafloor reconciliation markers.`);
