#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

// Execute the production browser function with a minimal DOM stub. This tests
// classification behavior, not full browser interaction.
const html = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");
const signature = "function updateEvidenceBridge(data) {";
const start = html.indexOf(signature);
assert.notEqual(start, -1, "updateEvidenceBridge must exist");
let depth = 0, quote = null, escaped = false, end = -1;
for (let i = start + signature.length - 1; i < html.length; i += 1) {
  const ch = html[i];
  if (quote) {
    if (escaped) escaped = false;
    else if (ch.charCodeAt(0) === 92) escaped = true;
    else if (ch === quote) quote = null;
    continue;
  }
  if (ch === "'" || ch === '"') quote = ch;
  else if (ch === "{") depth += 1;
  else if (ch === "}" && --depth === 0) { end = i + 1; break; }
}
assert.notEqual(end, -1, "function body must be balanced");
const productionFunction = html.slice(start, end);
const ids = [
  "bridge-scene-state", "bridge-track-count", "bridge-stable-count",
  "bridge-review-count", "bridge-source-state", "bridge-hardware-state",
  "bridge-conflict-count", "bridge-uncertainty-count",
  "bridge-calibration-count", "bridge-lineage-count", "bridge-scene-detail"
];
function runBridge(data) {
  const nodes = Object.create(null);
  for (const id of ids) nodes[id] = { textContent: "" };
  const context = { document: { getElementById: id => nodes[id] || null }, Object, Array, String, Number };
  vm.runInNewContext(productionFunction, context);
  context.updateEvidenceBridge(data);
  return nodes;
}
function track(overrides = {}) {
  return Object.assign({
    object_id: "T-1", uncertainty_m: 0.5, calibration_status: "verified",
    lineage_declared: true, conflict: false, modalities: [], sensor_ids: []
  }, overrides);
}
// Exactly 1 m is accepted; only values greater than 1 m trigger the gate.
{
  const n = runBridge({ model_id: "test", revision: "1", frame_id: "local", objects: [track({ uncertainty_m: 1 })] });
  assert.equal(n["bridge-track-count"].textContent, "1");
  assert.equal(n["bridge-stable-count"].textContent, "1");
  assert.equal(n["bridge-review-count"].textContent, "0");
  assert.equal(n["bridge-uncertainty-count"].textContent, "0");
}
// Above-threshold uncertainty.
{
  const n = runBridge({ objects: [track({ uncertainty_m: 1.01 })] });
  assert.equal(n["bridge-review-count"].textContent, "1");
  assert.equal(n["bridge-uncertainty-count"].textContent, "1");
}
// Missing uncertainty cannot silently pass.
{
  const n = runBridge({ objects: [track({ uncertainty_m: undefined })] });
  assert.equal(n["bridge-review-count"].textContent, "1");
  assert.equal(n["bridge-uncertainty-count"].textContent, "1");
}
// Calibration and lineage are independently counted.
{
  const n = runBridge({ objects: [track({ calibration_status: "unverified", lineage_declared: false })] });
  assert.equal(n["bridge-review-count"].textContent, "1");
  assert.equal(n["bridge-calibration-count"].textContent, "1");
  assert.equal(n["bridge-lineage-count"].textContent, "1");
}
// Explicit conflict.
{
  const n = runBridge({ objects: [track({ conflict: true })] });
  assert.equal(n["bridge-review-count"].textContent, "1");
  assert.equal(n["bridge-conflict-count"].textContent, "1");
}
// Mixed data verifies aggregate totals and overlapping gate counts.
{
  const n = runBridge({ objects: [
    track(), track({ conflict: true }), track({ uncertainty_m: null }),
    track({ calibration_status: "pending" }), track({ lineage_declared: false })
  ] });
  assert.equal(n["bridge-track-count"].textContent, "5");
  assert.equal(n["bridge-stable-count"].textContent, "1");
  assert.equal(n["bridge-review-count"].textContent, "4");
  assert.equal(n["bridge-conflict-count"].textContent, "1");
  assert.equal(n["bridge-uncertainty-count"].textContent, "1");
  assert.equal(n["bridge-calibration-count"].textContent, "1");
  assert.equal(n["bridge-lineage-count"].textContent, "1");
}
console.log("VIGIL spatial review logic: 6 scenario groups passed.");
